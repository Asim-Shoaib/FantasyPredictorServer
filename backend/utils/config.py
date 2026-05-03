from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


@dataclass
class PipelineConfig:
    root_dir: Path
    league_dirs: dict[str, str]
    people_csv: Path
    output_csv: Path
    role_cache_json: Path
    final_results_cache_parquet: Path
    request_delay_seconds: float = 0.02
    cutoff_years: int = 5

    @property
    def cutoff_date(self) -> date | None:
        if self.cutoff_years <= 0:
            return None
        return date.today() - timedelta(days=self.cutoff_years * 365)
