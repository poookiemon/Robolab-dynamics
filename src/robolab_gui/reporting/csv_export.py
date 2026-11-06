"""CSV audit exporter for protocol runs."""

import csv
from pathlib import Path
from typing import List, Dict, Any


class CSVExportService:
    """Exports run records to tabular CSV format."""

    @classmethod
    def export(cls, output_path: Path, records: List[Dict[str, Any]]) -> Path:
        fieldnames = ["step", "action", "slot", "well", "volume", "duration_seconds", "status"]
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in records:
                writer.writerow(r)
        return output_path
