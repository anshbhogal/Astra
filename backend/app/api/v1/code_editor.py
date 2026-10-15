import os
import shutil
import uuid
import mimetypes
from pathlib import Path
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.domain import User, UserRole, Project, ProjectMember, FailureAnalysisModel
from app.core.security import get_current_user
from app.core.rate_limit import limiter
from app.services.project_service import get_project_by_id

router = APIRouter(prefix="/projects/{project_id}/code", tags=["Code Studio / IDE"])

IGNORED_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules", ".idea", ".vscode"}
IGNORED_FILES = {".DS_Store", "thumbs.db"}


class FileNode(BaseModel):
    name: str
    path: str
    type: str  # "file" | "directory"
    size: Optional[int] = None
    children: Optional[List["FileNode"]] = None


class FileContentResponse(BaseModel):
    path: str
    content: str
    language: str
    size: int
    modified_at: str


class SaveFileRequest(BaseModel):
    path: str
    content: str


class CreateNodeRequest(BaseModel):
    path: str
    is_directory: bool = False
    content: Optional[str] = ""


class TestRunResultResponse(BaseModel):
    status: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    output: str
    duration_ms: float


def detect_language(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".json": "json",
        ".md": "markdown",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".sh": "shell",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".sql": "sql",
        ".xml": "xml",
        ".toml": "toml",
        ".ini": "ini",
        ".env": "shell",
        ".dockerfile": "dockerfile",
    }
    if os.path.basename(file_path).lower() == "dockerfile":
        return "dockerfile"
    return mapping.get(ext, "plaintext")


def safe_resolve(base_dir: Path, rel_path: str) -> Path:
    clean_rel = rel_path.lstrip("/\\")
    resolved = (base_dir / clean_rel).resolve()
    base_resolved = base_dir.resolve()
    if not str(resolved).startswith(str(base_resolved)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forbidden: path escapes project workspace."
        )
    return resolved


def ensure_workspace(project: Project) -> Path:
    candidates = [
        Path(f"/app/scratch/{project.id}"),
        Path(f"/app/workspaces/{project.id}/repository"),
    ]
    if "lecturerag" in project.repository_url.lower():
        candidates.append(Path("/app/scratch/lecturerag"))

    for c in candidates:
        if c.exists() and any(c.iterdir()):
            return c

    # Clone or scaffold
    scratch_dir = Path(f"/app/scratch/{project.id}")
    scratch_dir.mkdir(parents=True, exist_ok=True)
    try:
        from engine.analyzer.repo_cloner import GitRepoCloner
        cloner = GitRepoCloner()
        cloner.clone(project.repository_url, scratch_dir, branch=project.default_branch)
        return scratch_dir
    except Exception:
        # If clone fails (e.g. offline dummy git URL), create standard scaffold
        scratch_dir.mkdir(parents=True, exist_ok=True)
        readme = scratch_dir / "README.md"
        if not readme.exists():
            readme.write_text(
                f"# {project.name}\n\n"
                f"Repository: {project.repository_url}\n"
                f"Framework: {project.language_framework.value}\n\n"
                f"Welcome to Astra Code Studio! Edit files or add tests here.\n",
                encoding="utf-8"
            )
        main_py = scratch_dir / "main.py"
        if not main_py.exists():
            main_py.write_text(
                '"""Main service module for ' + project.name + '"""\n\n'
                'def add(a: int, b: int) -> int:\n'
                '    """Calculates sum of two numbers."""\n'
                '    return a + b\n\n'
                'def authenticate(user_token: str) -> bool:\n'
                '    """Authenticates API request token."""\n'
                '    if not user_token:\n'
                '        return False\n'
                '    return len(user_token) >= 10\n',
                encoding="utf-8"
            )
        return scratch_dir


def build_tree(base_dir: Path, current_dir: Path, max_depth: int = 5, current_depth: int = 0) -> List[FileNode]:
    if current_depth > max_depth:
        return []

    nodes: List[FileNode] = []
    try:
        entries = sorted(list(current_dir.iterdir()), key=lambda p: (not p.is_dir(), p.name.lower()))
    except (PermissionError, FileNotFoundError):
        return []

    for entry in entries:
        if entry.is_dir():
            if entry.name in IGNORED_DIRS:
                continue
            rel = str(entry.relative_to(base_dir)).replace("\\", "/")
            children = build_tree(base_dir, entry, max_depth, current_depth + 1)
            nodes.append(FileNode(
                name=entry.name,
                path=rel,
                type="directory",
                children=children
            ))
        elif entry.is_file():
            if entry.name in IGNORED_FILES:
                continue
            rel = str(entry.relative_to(base_dir)).replace("\\", "/")
            size = entry.stat().st_size if entry.exists() else 0
            nodes.append(FileNode(
                name=entry.name,
                path=rel,
                type="file",
                size=size
            ))
    return nodes


@router.get("/tree")
async def get_project_file_tree(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve full file tree of the project repository for the IDE file explorer."""
    project = await get_project_by_id(db, project_id, current_user)
    ws_dir = ensure_workspace(project)
    tree = build_tree(ws_dir, ws_dir)
    return {
        "project_id": str(project.id),
        "project_name": project.name,
        "default_branch": project.default_branch,
        "tree": tree
    }


@router.get("/file", response_model=FileContentResponse)
async def get_file_content(
    project_id: uuid.UUID,
    path: Optional[str] = Query(None, description="Relative file path"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Read file content to display in Monaco code editor."""
    project = await get_project_by_id(db, project_id, current_user)
    if not path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path parameter is required.")
    ws_dir = ensure_workspace(project)
    file_path = safe_resolve(ws_dir, path)

    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File '{path}' not found.")

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to read file: {exc}")

    stat = file_path.stat()
    return FileContentResponse(
        path=path,
        content=content,
        language=detect_language(path),
        size=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
    )


@router.put("/file")
async def save_file_content(
    project_id: uuid.UUID,
    payload: SaveFileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save modifications to a code file (Developer & Admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.DEVELOPER]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Developers and Administrators can edit code files.")

    project = await get_project_by_id(db, project_id, current_user)
    ws_dir = ensure_workspace(project)
    file_path = safe_resolve(ws_dir, payload.path)

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(payload.content, encoding="utf-8")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to write file: {exc}")

    return {
        "status": "SAVED",
        "path": payload.path,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "size": len(payload.content.encode("utf-8"))
    }


@router.post("/file", status_code=status.HTTP_201_CREATED)
async def create_file_or_dir(
    project_id: uuid.UUID,
    payload: CreateNodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new file or directory in the workspace (Developer & Admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.DEVELOPER]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Developers and Administrators can create files.")

    project = await get_project_by_id(db, project_id, current_user)
    ws_dir = ensure_workspace(project)
    target_path = safe_resolve(ws_dir, payload.path)

    if target_path.exists():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Item '{payload.path}' already exists.")

    try:
        if payload.is_directory:
            target_path.mkdir(parents=True, exist_ok=True)
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(payload.content or "", encoding="utf-8")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create: {exc}")

    return {"status": "CREATED", "path": payload.path}


@router.delete("/file")
async def delete_file_or_dir(
    project_id: uuid.UUID,
    path: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a file or directory from the workspace (Developer & Admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.DEVELOPER]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Developers and Administrators can delete files.")

    project = await get_project_by_id(db, project_id, current_user)
    ws_dir = ensure_workspace(project)
    target_path = safe_resolve(ws_dir, path)

    if not target_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Path does not exist.")

    try:
        if target_path.is_dir():
            shutil.rmtree(target_path)
        else:
            target_path.unlink()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete: {exc}")

    return {"status": "DELETED", "path": path}


@router.post("/run-tests", response_model=TestRunResultResponse)
@limiter.limit("10/hour")
async def run_developer_tests(
    request: Request,
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Execute unit tests on the developer's working directory so they can test their bug fix."""
    project = await get_project_by_id(db, project_id, current_user)
    ws_dir = ensure_workspace(project)

    from engine.analyzer.function_extractor import FunctionExtractor
    from engine.execution.unit_test_executor import UnitTestExecutor
    import time

    start_time = time.time()
    try:
        contracts = FunctionExtractor.extract_from_directory(str(ws_dir))
        if not contracts:
            return TestRunResultResponse(
                status="NO_TESTS_FOUND",
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                output="No callable functions discovered in this repository.",
                duration_ms=round((time.time() - start_time) * 1000, 2)
            )

        exec_result = UnitTestExecutor.execute_for_repo(str(ws_dir), contracts)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        output_lines = [
            f"=== Astra Developer Test Runner ===",
            f"Target Directory: {ws_dir}",
            f"Discovered Functions: {len(contracts)}",
            f"Total Executed Tests: {exec_result.total_tests}",
            f"Passed Tests: {exec_result.passed_tests}",
            f"Failed Tests: {exec_result.failed_tests}",
            f"Pass Rate: {exec_result.pass_rate * 100:.1f}%",
            f"Duration: {duration_ms}ms\n"
        ]

        for tr in exec_result.test_results:
            status_tag = "[PASS]" if tr.status == "PASSED" else "[FAIL]"
            output_lines.append(f"{status_tag} {tr.test_case_id} ({tr.execution_time_ms}ms)")
            if tr.status != "PASSED" and tr.error_message:
                output_lines.append(f"    Error: {tr.error_message}")

        return TestRunResultResponse(
            status="PASSED" if exec_result.failed_tests == 0 else "FAILED",
            total_tests=exec_result.total_tests,
            passed_tests=exec_result.passed_tests,
            failed_tests=exec_result.failed_tests,
            output="\n".join(output_lines),
            duration_ms=duration_ms
        )
    except Exception as exc:
        return TestRunResultResponse(
            status="ERROR",
            total_tests=0,
            passed_tests=0,
            failed_tests=1,
            output=f"Test runner error: {str(exc)}",
            duration_ms=round((time.time() - start_time) * 1000, 2)
        )


@router.get("/defects")
async def get_editor_defects(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve defect locations so developer can click directly into the failing file & line from the editor."""
    project = await get_project_by_id(db, project_id, current_user)
    stmt = (
        select(FailureAnalysisModel)
        .where(FailureAnalysisModel.project_id == project_id)
        .order_by(FailureAnalysisModel.created_at.desc())
    )
    defects = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": str(d.id),
            "summary": d.summary,
            "category": d.category,
            "status": d.status,
            "failing_file": d.failing_file,
            "failing_line": d.failing_line,
            "error_message": d.error_message,
        }
        for d in defects
    ]
