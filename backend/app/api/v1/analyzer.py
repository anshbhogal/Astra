import uuid
from typing import Optional
from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.analyzer import (
    AnalysisTriggerRequest,
    AnalysisResponse,
    EndpointCatalogResponse,
    KnowledgeGraphResponse,
    DiscoveredEndpointResponse,
    KnowledgeGraphNode,
    KnowledgeGraphEdge
)
from app.services import analyzer_service
from app.core.security import get_current_user
from app.core.rbac import require_roles
from app.models.domain import User, UserRole

router = APIRouter(prefix="/projects", tags=["Analyzer"])


@router.post("/{project_id}/analyze", response_model=AnalysisResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_analysis(
    project_id: uuid.UUID,
    payload: Optional[AnalysisTriggerRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_roles([UserRole.ADMIN, UserRole.DEVELOPER, UserRole.TESTER])
):
    """Trigger static code analysis for a project repository."""
    branch = payload.branch if payload else None
    analysis = await analyzer_service.trigger_project_analysis(db, project_id, branch, current_user)
    return analysis


@router.get("/{project_id}/analysis", response_model=AnalysisResponse)
async def get_latest_analysis(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve the latest analysis status for a project."""
    analysis = await analyzer_service.get_latest_project_analysis(db, project_id, current_user)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No analysis records found for this project."
        )
    return analysis


@router.get("/{project_id}/endpoints", response_model=EndpointCatalogResponse)
async def list_discovered_endpoints(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve paginated catalog of API endpoints discovered during analysis."""
    items, total = await analyzer_service.get_analysis_endpoints(
        db, project_id, current_user, page=page, page_size=page_size
    )
    return EndpointCatalogResponse(
        items=[DiscoveredEndpointResponse.model_validate(ep) for ep in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{project_id}/graph", response_model=KnowledgeGraphResponse)
async def get_project_knowledge_graph(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve Project Knowledge Graph (nodes and edges) for a project."""
    graph_dict = await analyzer_service.get_analysis_graph(db, project_id, current_user)
    nodes = [KnowledgeGraphNode(**n) for n in graph_dict.get("nodes", [])]
    edges = [KnowledgeGraphEdge(**e) for e in graph_dict.get("edges", [])]
    return KnowledgeGraphResponse(nodes=nodes, edges=edges)
