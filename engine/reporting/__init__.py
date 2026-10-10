"""Executive Quality Report Generation Module for ASTRA Phase 10."""

from .html_report_generator import HTMLReportGenerator
from .pdf_report_generator import PDFReportGenerator

__all__ = ["HTMLReportGenerator", "PDFReportGenerator"]
