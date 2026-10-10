"""REST Router for Phase 10 Quality Analytics, Defect Metrics & Executive Reporting."""

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Response, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.domain import User, UserRole, Project, QualityReportModel
from app.core.security import get_current_user
from app.services.analytics_service import AnalyticsService
from engine.reporting.html_report_generator import HTMLReportGenerator
from engine.reporting.pdf_report_generator import PDFReportGenerator

router = APIRouter()


class GenerateReportRequest(BaseModel):
    title: Optional[str] = Field("Executive Software Quality Audit Report", description="Custom report title")


async def _verify_project_access(project_id: uuid.UUID, current_user: User, db: AsyncSession) -> Project:
    stmt = select(Project).where(Project.id == project_id)
    res = await db.execute(stmt)
    project = res.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to access this project.",
        )

    return project


@router.get("/overview")
async def get_platform_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Platform-wide aggregate software quality KPIs across all tracked repositories."""
    return await AnalyticsService.get_platform_overview(db)


@router.get("/projects/{project_id}")
async def get_project_analytics(
    project_id: uuid.UUID,
    time_range: str = Query("30d", pattern="^(7d|30d|90d|all)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves near-real-time quality score, pass rate trends, and defect density for a project."""
    await _verify_project_access(project_id, current_user, db)
    return await AnalyticsService.get_project_analytics(db, project_id, time_range=time_range)


@router.post("/projects/{project_id}/reports")
async def generate_project_quality_report(
    project_id: uuid.UUID,
    req: GenerateReportRequest = GenerateReportRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generates and persists an executive quality audit report artifact with SHA256 checksum."""
    project = await _verify_project_access(project_id, current_user, db)
    analytics = await AnalyticsService.get_project_analytics(db, project_id)

    html_content = HTMLReportGenerator.generate_report_html(
        project_name=project.name,
        analytics_data=analytics,
        report_title=req.title or "Executive Software Quality Audit Report"
    )

    report = await AnalyticsService.create_quality_report(
        db=db,
        project_id=project_id,
        title=req.title or "Executive Software Quality Audit Report",
        quality_score=analytics["quality_score"],
        summary_metrics=analytics,
        html_content=html_content
    )

    return {
        "id": str(report.id),
        "title": report.title,
        "quality_score": report.quality_score,
        "sha256_hash": report.sha256_hash,
        "created_at": report.created_at.isoformat()
    }


@router.get("/projects/{project_id}/reports")
async def list_project_quality_reports(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists saved executive audit reports for a project."""
    await _verify_project_access(project_id, current_user, db)
    reports = await AnalyticsService.list_quality_reports(db, project_id)
    return [
        {
            "id": str(r.id),
            "title": r.title,
            "quality_score": r.quality_score,
            "sha256_hash": r.sha256_hash,
            "created_at": r.created_at.isoformat()
        }
        for r in reports
    ]


@router.get("/reports/{report_id}/export")
async def export_quality_report(
    report_id: uuid.UUID,
    format: str = Query("html", pattern="^(html|pdf)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exports executive report as downloadable HTML or PDF."""
    res = await db.execute(select(QualityReportModel).where(QualityReportModel.id == report_id))
    report = res.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Quality report not found.")

    await _verify_project_access(report.project_id, current_user, db)

    if format == "pdf":
        pdf_bytes, mime = PDFReportGenerator.generate_report(
            project_name=report.title,
            analytics_data=report.summary_metrics,
            report_title=report.title
        )
        return Response(
            content=pdf_bytes,
            media_type=mime,
            headers={"Content-Disposition": f'attachment; filename="astra_report_{str(report.id)[:8]}.pdf"'}
        )

    # Return standalone HTML
    return Response(
        content=report.html_content.encode("utf-8"),
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'inline; filename="astra_report_{str(report.id)[:8]}.html"'}
    )
