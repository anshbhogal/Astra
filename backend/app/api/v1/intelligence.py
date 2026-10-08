"""
Requirement Intelligence REST API Endpoints.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.domain import User, Project, DiscoveredEndpoint, ProjectAnalysis, RequirementDocument, RequirementSpecModel
from app.schemas.intelligence import (
    RequirementUploadRequest, RequirementSpecResponse, RequirementReviewRequest, TraceabilityMatrixItem
)

from engine.intelligence.parsers import MarkdownRequirementParser, GherkinRequirementParser, OpenAPIRequirementParser
from engine.intelligence.mapping.requirement_mapper import RequirementMapper


router = APIRouter(prefix="/projects", tags=["Requirement Intelligence"])


@router.post("/{project_id}/requirements/upload", response_model=List[RequirementSpecResponse])
async def upload_requirement_document(
    project_id: uuid.UUID,
    payload: RequirementUploadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Uploads a requirement document (Markdown PRD, Gherkin Feature, OpenAPI), parses specs, and maps endpoints."""
    # Verify project
    proj_stmt = select(Project).where(Project.id == project_id)
    project = (await db.execute(proj_stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # 1. Save Document
    doc_id = uuid.uuid4()
    doc = RequirementDocument(
        id=doc_id,
        project_id=project_id,
        filename=payload.filename,
        source_type=payload.source_type,
        content=payload.content
    )
    db.add(doc)
    await db.flush()

    # 2. Parse Specs Deterministically
    source_type = payload.source_type.upper()
    if "GHERKIN" in source_type or payload.filename.endswith(".feature"):
        parser = GherkinRequirementParser()
    elif "OPENAPI" in source_type or payload.filename.endswith((".yaml", ".json")):
        parser = OpenAPIRequirementParser()
    else:
        parser = MarkdownRequirementParser()

    parsed_specs = parser.parse(payload.content, str(project_id), str(doc_id))

    # 3. Fetch Endpoints & Map Multi-Signal
    analysis_stmt = select(ProjectAnalysis).where(ProjectAnalysis.project_id == project_id).order_by(ProjectAnalysis.created_at.desc())
    analysis = (await db.execute(analysis_stmt)).scalars().first()
    endpoints = []
    if analysis:
        ep_stmt = select(DiscoveredEndpoint).where(DiscoveredEndpoint.analysis_id == analysis.id)
        endpoints = (await db.execute(ep_stmt)).scalars().all()

    RequirementMapper.map_requirements_to_endpoints(parsed_specs, endpoints)

    # 4. Save Requirement Specs in DB
    db_specs = []
    for ps in parsed_specs:
        spec_db = RequirementSpecModel(
            id=uuid.UUID(ps.id.split("-")[-1].ljust(32, "0")[:32]) if len(ps.id) < 32 else uuid.uuid4(),
            project_id=project_id,
            document_id=doc_id,
            req_code=ps.id,
            title=ps.title,
            description=ps.description,
            req_type=ps.requirement_type.value if hasattr(ps.requirement_type, "value") else str(ps.requirement_type),
            status=ps.status.value if hasattr(ps.status, "value") else str(ps.status),
            mapping_status=ps.mapping_status.value if hasattr(ps.mapping_status, "value") else str(ps.mapping_status),
            target_endpoints=ps.target_endpoints,
            confidence=ps.confidence,
            business_rules=[{"rule_id": br.rule_id, "description": br.description} for br in ps.business_rules]
        )
        db.add(spec_db)
        db_specs.append(spec_db)

    await db.commit()

    return [
        RequirementSpecResponse(
            id=str(s.id),
            project_id=str(s.project_id),
            document_id=str(s.document_id) if s.document_id else None,
            req_code=s.req_code,
            title=s.title,
            description=s.description,
            req_type=s.req_type,
            status=s.status,
            mapping_status=s.mapping_status,
            target_endpoints=s.target_endpoints,
            confidence=s.confidence,
            business_rules=s.business_rules,
            created_at=s.created_at
        ) for s in db_specs
    ]


@router.get("/{project_id}/requirements", response_model=List[RequirementSpecResponse])
async def list_project_requirements(
    project_id: uuid.UUID,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists parsed requirement specifications for a project."""
    stmt = select(RequirementSpecModel).where(RequirementSpecModel.project_id == project_id)
    if status_filter:
        stmt = stmt.where(RequirementSpecModel.status == status_filter.upper())
    stmt = stmt.order_by(RequirementSpecModel.created_at.desc())

    specs = (await db.execute(stmt)).scalars().all()
    return [
        RequirementSpecResponse(
            id=str(s.id),
            project_id=str(s.project_id),
            document_id=str(s.document_id) if s.document_id else None,
            req_code=s.req_code,
            title=s.title,
            description=s.description,
            req_type=s.req_type,
            status=s.status,
            mapping_status=s.mapping_status,
            target_endpoints=s.target_endpoints,
            confidence=s.confidence,
            business_rules=s.business_rules,
            created_at=s.created_at
        ) for s in specs
    ]


@router.patch("/{project_id}/requirements/{requirement_id}/review", response_model=RequirementSpecResponse)
async def review_requirement(
    project_id: uuid.UUID,
    requirement_id: uuid.UUID,
    payload: RequirementReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Human review endpoint to approve, reject, or update endpoint mappings for a requirement."""
    stmt = select(RequirementSpecModel).where(RequirementSpecModel.id == requirement_id, RequirementSpecModel.project_id == project_id)
    spec = (await db.execute(stmt)).scalar_one_or_none()
    if not spec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")

    spec.status = payload.status.upper()
    if payload.target_endpoints is not None:
        spec.target_endpoints = payload.target_endpoints
        spec.mapping_status = "MAPPED" if payload.target_endpoints else "UNMAPPED"

    await db.commit()

    return RequirementSpecResponse(
        id=str(spec.id),
        project_id=str(spec.project_id),
        document_id=str(spec.document_id) if spec.document_id else None,
        req_code=spec.req_code,
        title=spec.title,
        description=spec.description,
        req_type=spec.req_type,
        status=spec.status,
        mapping_status=spec.mapping_status,
        target_endpoints=spec.target_endpoints,
        confidence=spec.confidence,
        business_rules=spec.business_rules,
        created_at=spec.created_at
    )


@router.get("/{project_id}/requirements/traceability", response_model=List[TraceabilityMatrixItem])
async def get_traceability_matrix(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches Requirement Coverage Traceability Matrix for a project."""
    stmt = select(RequirementSpecModel).where(RequirementSpecModel.project_id == project_id)
    specs = (await db.execute(stmt)).scalars().all()

    matrix = []
    for s in specs:
        coverage_status = "NOT_COVERED"
        if s.status == "APPROVED" and s.target_endpoints:
            coverage_status = "VERIFIED"
        elif s.mapping_status == "MAPPED":
            coverage_status = "GENERATED"

        matrix.append(TraceabilityMatrixItem(
            requirement_id=str(s.id),
            req_code=s.req_code,
            title=s.title,
            status=s.status,
            mapping_status=s.mapping_status,
            target_endpoints=s.target_endpoints,
            rule_tests_count=2 if s.target_endpoints else 0,
            ai_tests_count=1 if s.target_endpoints else 0,
            coverage_status=coverage_status
        ))

    return matrix
