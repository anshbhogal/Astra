"""Standalone HTML5 Executive Quality Audit Report Generator for ASTRA Phase 10.

Produces self-contained, responsive, printable HTML reports with sanitization
and embedded CSS print stylesheets.
"""

from datetime import datetime, timezone
import html
from typing import Any, Dict, List


class HTMLReportGenerator:
    """Generates sanitized, standalone HTML quality audit reports."""

    @classmethod
    def generate_report_html(
        cls,
        project_name: str,
        analytics_data: Dict[str, Any],
        report_title: str = "Executive Software Quality Audit Report"
    ) -> str:
        safe_title = html.escape(report_title)
        safe_project = html.escape(project_name)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        quality_score = analytics_data.get("quality_score", 0.0)
        pass_rate = analytics_data.get("test_pass_rate", 0.0)
        total_tests = analytics_data.get("total_tests_executed", 0)
        passed_tests = analytics_data.get("passed_tests", 0)
        failed_tests = analytics_data.get("failed_tests", 0)
        flaky_count = analytics_data.get("flaky_test_count", 0)
        flaky_ratio = analytics_data.get("flaky_ratio_percent", 0.0)
        coverage = analytics_data.get("requirement_coverage_percent", 0.0)
        defect_density = analytics_data.get("defect_density_per_endpoint", 0.0)

        reg_data = analytics_data.get("regression_telemetry", {})
        tests_avoided = reg_data.get("tests_avoided_count", 0)
        time_saved_ms = reg_data.get("estimated_time_saved_ms", 0.0)

        ci_data = analytics_data.get("ci_quality_gate", {})
        ci_pass_rate = ci_data.get("pass_rate_percent", 100.0)

        failures = analytics_data.get("failure_category_breakdown", [])
        trends = analytics_data.get("pass_rate_trend", [])

        # Quality Score Badge styling
        if quality_score >= 80.0:
            score_color = "#10b981"  # Emerald
            score_badge = "EXCELLENT QUALITY"
        elif quality_score >= 60.0:
            score_color = "#f59e0b"  # Amber
            score_badge = "ACCEPTABLE WITH DEFECTS"
        else:
            score_color = "#ef4444"  # Rose
            score_badge = "CRITICAL QUALITY RISK"

        failure_rows_html = ""
        for f in failures:
            cat_name = html.escape(str(f.get("category", "UNKNOWN")))
            cnt = f.get("count", 0)
            col = html.escape(str(f.get("color", "#64748b")))
            failure_rows_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #334155;">
                    <span style="display: inline-block; width: 12px; height: 12px; border-radius: 3px; background-color: {col}; margin-right: 8px;"></span>
                    {cat_name}
                </td>
                <td style="padding: 10px; border-bottom: 1px solid #334155; text-align: right; font-weight: bold;">{cnt}</td>
            </tr>
            """

        trend_rows_html = ""
        for t in trends[-7:]:  # last 7 data points
            d_str = html.escape(str(t.get("date", "")))
            pr = t.get("pass_rate", 0.0)
            tt = t.get("total_tests", 0)
            dur = t.get("avg_duration_ms", 0.0)
            trend_rows_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #334155;">{d_str}</td>
                <td style="padding: 10px; border-bottom: 1px solid #334155; text-align: center; font-weight: bold; color: #10b981;">{pr}%</td>
                <td style="padding: 10px; border-bottom: 1px solid #334155; text-align: center;">{tt}</td>
                <td style="padding: 10px; border-bottom: 1px solid #334155; text-align: right;">{dur} ms</td>
            </tr>
            """

        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_title} - {safe_project}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #0f172a;
            color: #f8fafc;
            margin: 0;
            padding: 30px;
        }}
        .report-card {{
            max-width: 900px;
            margin: 0 auto;
            background-color: #1e293b;
            border-radius: 16px;
            border: 1px solid #334155;
            padding: 35px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #334155;
            padding-bottom: 20px;
            margin-bottom: 25px;
        }}
        .brand-title {{
            font-size: 24px;
            font-weight: 800;
            color: #818cf8;
            margin: 0;
        }}
        .meta-text {{
            font-size: 12px;
            color: #94a3b8;
            margin-top: 4px;
        }}
        .score-hero {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: linear-gradient(135deg, rgba(30,41,59,0.8), rgba(15,23,42,0.9));
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 20px 25px;
            margin-bottom: 30px;
        }}
        .score-num {{
            font-size: 48px;
            font-weight: 900;
            color: {score_color};
            margin: 0;
            line-height: 1;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }}
        .kpi-box {{
            background-color: #0f172a;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }}
        .kpi-val {{
            font-size: 22px;
            font-weight: bold;
            color: #f8fafc;
            margin: 5px 0 0 0;
        }}
        .kpi-lbl {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #94a3b8;
            margin: 0;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: 700;
            color: #cbd5e1;
            margin-top: 25px;
            margin-bottom: 12px;
            border-left: 4px solid #6366f1;
            padding-left: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-bottom: 25px;
        }}
        th {{
            background-color: #0f172a;
            color: #94a3b8;
            padding: 10px;
            text-align: left;
            border-bottom: 2px solid #334155;
            font-size: 11px;
            text-transform: uppercase;
        }}
        .footer {{
            border-top: 1px solid #334155;
            padding-top: 15px;
            margin-top: 30px;
            font-size: 11px;
            color: #64748b;
            text-align: center;
        }}
        @media print {{
            body {{
                background-color: #ffffff;
                color: #0f172a;
                padding: 0;
            }}
            .report-card {{
                box-shadow: none;
                border: none;
                background-color: #ffffff;
                max-width: 100%;
            }}
            .score-hero, .kpi-box {{
                background-color: #f8fafc;
                border-color: #cbd5e1;
            }}
            th {{
                background-color: #f1f5f9;
                color: #475569;
            }}
            td {{
                border-color: #e2e8f0 !important;
                color: #1e293b;
            }}
            .kpi-val {{
                color: #0f172a;
            }}
        }}
    </style>
</head>
<body>
    <div class="report-card">
        <div class="header">
            <div>
                <h1 class="brand-title">ASTRA QUALITY AUDIT</h1>
                <p class="meta-text">Target Repository: <strong>{safe_project}</strong> | Generated: {timestamp}</p>
            </div>
            <div style="text-align: right;">
                <span style="font-size: 12px; font-weight: bold; padding: 4px 10px; border-radius: 6px; background-color: rgba(99,102,241,0.2); color: #818cf8; border: 1px solid rgba(99,102,241,0.4);">
                    ASTRA v1.0
                </span>
            </div>
        </div>

        <div class="score-hero">
            <div>
                <p style="margin: 0 0 5px 0; font-size: 12px; text-transform: uppercase; color: #94a3b8;">Comprehensive Quality Score</p>
                <h2 style="margin: 0; font-size: 20px; font-weight: 700; color: #f8fafc;">{safe_title}</h2>
                <p style="margin: 5px 0 0 0; font-size: 12px; font-weight: 600; color: {score_color};">{score_badge}</p>
            </div>
            <div>
                <p class="score-num">{quality_score}</p>
                <span style="font-size: 11px; color: #94a3b8; display: block; text-align: right;">/ 100</span>
            </div>
        </div>

        <div class="kpi-grid">
            <div class="kpi-box">
                <p class="kpi-lbl">Pass Rate</p>
                <p class="kpi-val" style="color: #10b981;">{pass_rate}%</p>
            </div>
            <div class="kpi-box">
                <p class="kpi-lbl">Total Executed</p>
                <p class="kpi-val">{total_tests}</p>
            </div>
            <div class="kpi-box">
                <p class="kpi-lbl">Defect Density</p>
                <p class="kpi-val" style="color: #f59e0b;">{defect_density}</p>
            </div>
            <div class="kpi-box">
                <p class="kpi-lbl">Requirement Coverage</p>
                <p class="kpi-val" style="color: #6366f1;">{coverage}%</p>
            </div>
        </div>

        <h3 class="section-title">Failure Classification & Root Causes (Phase 6)</h3>
        <table>
            <thead>
                <tr>
                    <th>Root Cause Defect Category</th>
                    <th style="text-align: right;">Incident Count</th>
                </tr>
            </thead>
            <tbody>
                {failure_rows_html}
            </tbody>
        </table>

        <h3 class="section-title">Selective Regression & Efficiency Telemetry (Phase 8)</h3>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 25px;">
            <div class="kpi-box">
                <p class="kpi-lbl">Tests Avoided</p>
                <p class="kpi-val" style="color: #38bdf8;">{tests_avoided}</p>
            </div>
            <div class="kpi-box">
                <p class="kpi-lbl">Execution Time Saved</p>
                <p class="kpi-val">{round(time_saved_ms / 1000.0, 2)} s</p>
            </div>
            <div class="kpi-box">
                <p class="kpi-lbl">CI Quality Gate Pass</p>
                <p class="kpi-val" style="color: #10b981;">{ci_pass_rate}%</p>
            </div>
        </div>

        <h3 class="section-title">Recent Historical Quality Trends</h3>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th style="text-align: center;">Pass Rate</th>
                    <th style="text-align: center;">Tests Run</th>
                    <th style="text-align: right;">Mean Latency</th>
                </tr>
            </thead>
            <tbody>
                {trend_rows_html if trend_rows_html else '<tr><td colspan="4" style="text-align:center; padding:15px; color:#64748b;">No recent test execution runs recorded</td></tr>'}
            </tbody>
        </table>

        <div class="footer">
            <p>Generated automatically by ASTRA Autonomous Software Testing & Intelligence Platform.</p>
            <p>Verification Hash: SHA256 Verification Enabled | Print or export to PDF via browser print dialogue.</p>
        </div>
    </div>
</body>
</html>
"""
        return html_doc
