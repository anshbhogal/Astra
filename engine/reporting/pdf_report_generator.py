"""PDF Quality Report Generator with Printable HTML Fallback for ASTRA Phase 10.

Uses ReportLab when available to generate binary PDF audit reports, with automatic
graceful fallback to self-contained printable HTML5 documents.
"""

import io
import logging
from typing import Any, Dict, Tuple
from engine.reporting.html_report_generator import HTMLReportGenerator

logger = logging.getLogger(__name__)


class PDFReportGenerator:
    """Generates PDF documents or returns printable HTML fallback if ReportLab is unavailable."""

    @classmethod
    def generate_report(
        cls,
        project_name: str,
        analytics_data: Dict[str, Any],
        report_title: str = "Executive Software Quality Audit Report"
    ) -> Tuple[bytes, str]:
        """Generates report bytes and returns tuple (content_bytes, mime_type).

        Returns:
            Tuple[bytes, str]: (bytes, "application/pdf" or "text/html; charset=utf-8")
        """
        # Always build HTML as base representation
        html_content = HTMLReportGenerator.generate_report_html(
            project_name=project_name,
            analytics_data=analytics_data,
            report_title=report_title
        )

        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
            styles = getSampleStyleSheet()

            elements = []

            # Title
            title_style = ParagraphStyle(
                'ReportTitle',
                parent=styles['Heading1'],
                fontSize=20,
                textColor=colors.HexColor("#4338ca"),
                spaceAfter=12
            )
            elements.append(Paragraph(f"ASTRA QUALITY AUDIT: {report_title}", title_style))
            elements.append(Paragraph(f"Target Project: {project_name}", styles['Normal']))
            elements.append(Spacer(1, 15))

            # Quality Score & KPIs Table
            score_data = [
                ["Quality Score", f"{analytics_data.get('quality_score', 0.0)} / 100"],
                ["Test Pass Rate", f"{analytics_data.get('test_pass_rate', 0.0)}%"],
                ["Total Executed Tests", str(analytics_data.get('total_tests_executed', 0))],
                ["Defect Density", str(analytics_data.get('defect_density_per_endpoint', 0.0))],
                ["Requirement Coverage", f"{analytics_data.get('requirement_coverage_percent', 0.0)}%"],
            ]
            t = Table(score_data, colWidths=[200, 200])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e0e7ff")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#312e81")),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 20))

            # Build PDF
            doc.build(elements)
            pdf_bytes = buffer.getvalue()
            buffer.close()
            return pdf_bytes, "application/pdf"

        except Exception as exc:
            logger.info("PDF generation with printable HTML fallback (ReportLab fallback triggered: %s)", exc)
            return html_content.encode("utf-8"), "text/html; charset=utf-8"
