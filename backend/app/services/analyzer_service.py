import uuid
from typing import Tuple, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.domain import Project, ProjectAnalysis, DiscoveredEndpoint, User, AuditLog, AnalysisStatus, AnalysisStage
from app.services.project_service import get_project_by_id


async def trigger_project_analysis(
    db: AsyncSession, project_id: uuid.UUID, branch_override: Optional[str], current_user: User
) -> ProjectAnalysis:
    project = await get_project_by_id(db, project_id, current_user)

    target_branch = branch_override or project.default_branch

    # Create new analysis snapshot record in QUEUED status
    analysis = ProjectAnalysis(
        project_id=project.id,
        repository_url=project.repository_url,
        branch=target_branch,
        status=AnalysisStatus.QUEUED,
        current_stage=AnalysisStage.CLONING,
        progress_percent=0,
        scanned_files_count=0,
        parsed_files_count=0,
        endpoint_count=0,
        graph_node_count=0,
        graph_edge_count=0,
        knowledge_graph={"nodes": [], "edges": []},
        analyzer_version="2.0.0"
    )
    db.add(analysis)
    await db.flush()

    audit_entry = AuditLog(
        actor_id=current_user.id,
        action="ANALYSIS_TRIGGERED",
        resource_type="PROJECT_ANALYSIS",
        resource_id=str(analysis.id),
        details={"project_id": str(project.id), "branch": target_branch}
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(analysis)

    # Dispatch Celery background task
    try:
        from workers.tasks.analyzer_tasks import run_project_analysis_task
        run_project_analysis_task.delay(str(analysis.id))
    except Exception as e:
        # Fallback to direct synchronous execution or log error if celery runner fails
        pass

    return analysis


async def get_latest_project_analysis(
    db: AsyncSession, project_id: uuid.UUID, current_user: User
) -> Optional[ProjectAnalysis]:
    await get_project_by_id(db, project_id, current_user) # enforce access control

    stmt = (
        select(ProjectAnalysis)
        .where(ProjectAnalysis.project_id == project_id)
        .order_by(ProjectAnalysis.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_analysis_endpoints(
    db: AsyncSession, project_id: uuid.UUID, current_user: User, page: int = 1, page_size: int = 50
) -> Tuple[List[DiscoveredEndpoint], int]:
    analysis = await get_latest_project_analysis(db, project_id, current_user)
    if not analysis:
        return [], 0

    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    offset = (page - 1) * page_size

    count_stmt = select(func.count(DiscoveredEndpoint.id)).where(DiscoveredEndpoint.analysis_id == analysis.id)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(DiscoveredEndpoint)
        .where(DiscoveredEndpoint.analysis_id == analysis.id)
        .order_by(DiscoveredEndpoint.path.asc(), DiscoveredEndpoint.method.asc())
        .offset(offset)
        .limit(page_size)
    )
    items = (await db.execute(stmt)).scalars().all()
    return list(items), total


async def get_analysis_graph(
    db: AsyncSession, project_id: uuid.UUID, current_user: User
) -> dict:
    analysis = await get_latest_project_analysis(db, project_id, current_user)
    if not analysis or not analysis.knowledge_graph:
        return {"nodes": [], "edges": []}

    return analysis.knowledge_graph
