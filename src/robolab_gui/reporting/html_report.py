"""Automated HTML run report generator."""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


class HTMLReportGenerator:
    """Renders formatted HTML dashboards summarizing protocol execution."""

    @classmethod
    def generate(
        cls,
        output_path: Path,
        protocol_name: str,
        station_id: str,
        status: str,
        total_steps: int,
        elapsed_seconds: float,
        step_records: List[Dict[str, Any]] = None,
    ) -> Path:
        records = step_records or []
        mins = int(elapsed_seconds // 60)
        secs = int(elapsed_seconds % 60)
        dur_str = f"{mins}m {secs}s"

        rows_html = ""
        for r in records[:50]:  # preview first 50
            rows_html += f"""
            <tr>
                <td>{r.get('step', '-')}</td>
                <td>{r.get('action', '-')}</td>
                <td>{r.get('slot', '-')}</td>
                <td>{r.get('well', '-')}</td>
                <td>{r.get('volume', 0.0):.1f}</td>
                <td><span class="badge success">{r.get('status', 'OK')}</span></td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>RoboLab Run Report - {protocol_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 30px; background: #f8f9fa; color: #333; }}
        .card {{ background: white; border-radius: 8px; padding: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); margin-bottom: 20px; }}
        h1 {{ margin-top: 0; color: #1a73e8; }}
        .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; }}
        .metric {{ background: #f1f3f4; padding: 15px; border-radius: 6px; }}
        .metric-title {{ font-size: 12px; color: #5f6368; text-transform: uppercase; }}
        .metric-val {{ font-size: 20px; font-weight: bold; margin-top: 4px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ padding: 10px; border-bottom: 1px solid #e0e0e0; text-align: left; font-size: 13px; }}
        th {{ background: #fafafa; font-weight: 600; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
        .badge.success {{ background: #e6f4ea; color: #137333; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>RoboLab Automated Run Report</h1>
        <div class="grid">
            <div class="metric"><div class="metric-title">Protocol</div><div class="metric-val">{protocol_name}</div></div>
            <div class="metric"><div class="metric-title">Station</div><div class="metric-val">{station_id}</div></div>
            <div class="metric"><div class="metric-title">Status</div><div class="metric-val">{status}</div></div>
            <div class="metric"><div class="metric-title">Duration</div><div class="metric-val">{dur_str}</div></div>
        </div>
    </div>
    <div class="card">
        <h3>Execution Step Audit ({len(records)} steps recorded)</h3>
        <table>
            <thead>
                <tr><th>#</th><th>Action</th><th>Slot</th><th>Well</th><th>Volume (uL)</th><th>Status</th></tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
        output_path.write_text(html_content, encoding="utf-8")
        return output_path
