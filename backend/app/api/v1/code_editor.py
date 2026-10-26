import os
import shutil
import uuid
import mimetypes
import git
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


class GitStatusResponse(BaseModel):
    branch: str
    is_clean: bool
    modified_files: List[str]
    untracked_files: List[str]
    staged_files: List[str]


class GitCommitRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    files: Optional[List[str]] = None


class GitCommitResponse(BaseModel):
    commit_sha: str
    branch: str
    message: str
    author_name: str
    author_email: str
    committed_at: str
    files_changed: int


class GitBranchRequest(BaseModel):
    branch_name: str = Field(..., min_length=1, max_length=100)
    create_and_checkout: bool = True


class GitBranchResponse(BaseModel):
    current_branch: str
    branches: List[str]


class GitDiffResponse(BaseModel):
    diff: str
    files_changed: List[str]


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


def get_git_repo(ws_dir: Path, default_branch: str = "main") -> git.Repo:
    try:
        repo = git.Repo(ws_dir)
    except (git.exc.InvalidGitRepositoryError, git.exc.NoSuchPathError):
        repo = git.Repo.init(ws_dir, initial_branch=default_branch)
        with repo.config_writer() as config:
            if not config.has_section("user"):
                config.add_section("user")
            config.set_value("user", "name", "ASTRA Developer")
            config.set_value("user", "email", "dev@astra.local")
        
        entries = [e for e in ws_dir.iterdir() if e.name != ".git"]
        if entries:
            repo.git.add(A=True)
            if repo.is_dirty() or repo.untracked_files:
                author = git.Actor("ASTRA Developer", "dev@astra.local")
                repo.index.commit("Initial repository scaffold", author=author, committer=author)
    return repo


def ensure_workspace(project: Project) -> Path:
    candidates = [
        Path(f"/app/scratch/{project.id}"),
        Path(f"/app/workspaces/{project.id}/repository"),
    ]
    if "lecturerag" in project.repository_url.lower():
        candidates.append(Path("/app/scratch/lecturerag"))

    for c in candidates:
        if c.exists() and any(c.iterdir()):
            get_git_repo(c, project.default_branch)
            return c

    # Clone or scaffold
    scratch_dir = Path(f"/app/scratch/{project.id}")
    scratch_dir.mkdir(parents=True, exist_ok=True)
    try:
        from engine.analyzer.repo_cloner import GitRepoCloner
        cloner = GitRepoCloner()
        cloner.clone(project.repository_url, scratch_dir, branch=project.default_branch)
        get_git_repo(scratch_dir, project.default_branch)
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
        get_git_repo(scratch_dir, project.default_branch)
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


@router.get("/git/status", response_model=GitStatusResponse)
async def get_git_status(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve git status of the project workspace."""
    project = await get_project_by_id(db, project_id, current_user)
    ws_dir = ensure_workspace(project)
    repo = get_git_repo(ws_dir, project.default_branch)

    try:
        current_branch = repo.active_branch.name
    except TypeError:
        current_branch = "HEAD"

    # Changed files compared to index
    modified = [item.a_path for item in repo.index.diff(None)]
    # Staged files compared to HEAD
    try:
        staged = [item.a_path for item in repo.index.diff("HEAD")]
    except Exception:
        staged = []
    untracked = list(repo.untracked_files)

    is_clean = not bool(modified or staged or untracked)

    return GitStatusResponse(
        branch=current_branch,
        is_clean=is_clean,
        modified_files=modified,
        untracked_files=untracked,
        staged_files=staged
    )


@router.get("/git/diff", response_model=GitDiffResponse)
async def get_git_diff(
    project_id: uuid.UUID,
    path: Optional[str] = Query(None, description="Optional relative file path to diff"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve unified git diff for working tree or specific file."""
    project = await get_project_by_id(db, project_id, current_user)
    ws_dir = ensure_workspace(project)
    repo = get_git_repo(ws_dir, project.default_branch)

    files_changed: List[str] = []
    diff_text = ""

    try:
        if path:
            file_path = safe_resolve(ws_dir, path)
            rel_path = str(file_path.relative_to(ws_dir)).replace("\\", "/")
            diff_text = repo.git.diff("HEAD", rel_path)
            if diff_text:
                files_changed = [rel_path]
        else:
            diff_text = repo.git.diff("HEAD")
            diff_index = repo.index.diff(None)
            files_changed = [d.a_path for d in diff_index]
    except Exception:
        diff_text = repo.git.diff()

    return GitDiffResponse(diff=diff_text, files_changed=files_changed)


@router.get("/git/branches", response_model=GitBranchResponse)
async def list_git_branches(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all local git branches in the workspace."""
    project = await get_project_by_id(db, project_id, current_user)
    ws_dir = ensure_workspace(project)
    repo = get_git_repo(ws_dir, project.default_branch)

    try:
        current_branch = repo.active_branch.name
    except TypeError:
        current_branch = "HEAD"

    branches = [h.name for h in repo.heads]
    if not branches and current_branch:
        branches = [current_branch]

    return GitBranchResponse(current_branch=current_branch, branches=branches)


@router.post("/git/branches", response_model=GitBranchResponse)
async def create_or_checkout_branch(
    project_id: uuid.UUID,
    payload: GitBranchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create or switch to a branch (Developer & Admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.DEVELOPER]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Developers and Administrators can manage branches.")

    project = await get_project_by_id(db, project_id, current_user)
    ws_dir = ensure_workspace(project)
    repo = get_git_repo(ws_dir, project.default_branch)

    branch_name = payload.branch_name.strip()
    if not branch_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Branch name cannot be empty.")

    try:
        existing_heads = [h.name for h in repo.heads]
        if branch_name in existing_heads:
            repo.git.checkout(branch_name)
        else:
            repo.git.checkout("-b", branch_name)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to switch/create branch: {exc}")

    try:
        current_branch = repo.active_branch.name
    except TypeError:
        current_branch = branch_name

    branches = [h.name for h in repo.heads]
    return GitBranchResponse(current_branch=current_branch, branches=branches)


@router.post("/git/commit", response_model=GitCommitResponse)
async def commit_changes(
    project_id: uuid.UUID,
    payload: GitCommitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Commit changes to the workspace repository with authenticated author attribution (Developer & Admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.DEVELOPER]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Developers and Administrators can commit changes.")

    project = await get_project_by_id(db, project_id, current_user)
    ws_dir = ensure_workspace(project)
    repo = get_git_repo(ws_dir, project.default_branch)

    if payload.files:
        for f in payload.files:
            file_path = safe_resolve(ws_dir, f)
            rel_path = str(file_path.relative_to(ws_dir)).replace("\\", "/")
            repo.git.add(rel_path)
    else:
        repo.git.add(A=True)

    if not repo.is_dirty() and not repo.untracked_files:
        try:
            if not repo.index.diff("HEAD"):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No changes to commit (working tree clean).")
        except Exception:
            pass

    author = git.Actor(
        current_user.full_name or "ASTRA Developer",
        current_user.email or "dev@astra.local"
    )

    try:
        commit = repo.index.commit(
            payload.message,
            author=author,
            committer=author
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Git commit failed: {exc}")

    try:
        current_branch = repo.active_branch.name
    except TypeError:
        current_branch = "HEAD"

    return GitCommitResponse(
        commit_sha=commit.hexsha,
        branch=current_branch,
        message=commit.message.strip(),
        author_name=author.name,
        author_email=author.email,
        committed_at=datetime.fromtimestamp(commit.committed_date, timezone.utc).isoformat(),
        files_changed=len(commit.stats.files)
    )
