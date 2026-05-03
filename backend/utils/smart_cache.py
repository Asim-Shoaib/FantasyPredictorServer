from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from backend.jobs.match_parser import MatchParser


class SmartMatchCache:
    """Maintains a single final_results_cache.parquet for parsed records.

    Guarantees:
    - Each match_id is only parsed once.  Subsequent runs skip already-cached
      matches so the parquet never grows with duplicate rows.
    - save_cache() is a no-op when nothing new was parsed.
    - A final drop_duplicates(match_id, player_id) guards against any legacy
      duplicates already present in the file.
    """

    def __init__(self, final_results_cache_path: Path) -> None:
        self.final_results_cache_path = final_results_cache_path
        self.cache_dir = self.final_results_cache_path.parent
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.new_records: list[dict[str, Any]] = []
        # Load the set of already-cached match IDs once at startup so that
        # get_or_parse_match can skip them without reading the whole parquet.
        self._cached_match_ids: set[str] = self._load_cached_match_ids()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_cached_match_ids(self) -> set[str]:
        """Return the set of match_ids already stored in the parquet cache."""
        if not self.final_results_cache_path.exists():
            return set()
        try:
            df = pd.read_parquet(self.final_results_cache_path, columns=["match_id"])
            return set(df["match_id"].dropna().astype(str).unique())
        except (OSError, ValueError, KeyError):
            return set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_or_parse_match(
        self,
        league: str,
        file_path: Path,
        parser: MatchParser,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Return records for this match, parsing only if not already cached.

        Returns
        -------
        (records, is_new)
            records  – list of row dicts (empty if pulled from parquet cache)
            is_new   – True if the match was freshly parsed this run
        """
        match_id = file_path.stem
        if match_id in self._cached_match_ids:
            # Already in parquet; Pipeline.run() will load it via
            # load_all_cached_records() — no need to return rows here.
            return [], False

        parsed = parser.parse_match(league, file_path)
        records = [asdict(pdata) for pdata in parsed.values()]
        self.new_records.extend(records)
        self._cached_match_ids.add(match_id)   # prevent double-parse if called twice
        return records, True

    def load_all_cached_records(self, cutoff_date: date | None = None) -> list[dict[str, Any]]:
        """Load all records from parquet, optionally filtered by cutoff_date."""
        if self.final_results_cache_path.exists():
            try:
                df = pd.read_parquet(self.final_results_cache_path)
                if cutoff_date is not None and "match_date" in df.columns:
                    df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
                    df = df[df["match_date"] >= pd.Timestamp(cutoff_date)]
                return df.to_dict(orient="records")
            except (OSError, ValueError):
                pass
        return []

    def save_cache(self) -> None:
        """Persist new records to parquet; no-op if nothing was newly parsed."""
        if not self.new_records:
            return  # Nothing to do — avoids unnecessary I/O

        existing_records = self.load_all_cached_records()
        all_records = existing_records + self.new_records
        df = pd.DataFrame(all_records)
        if df.empty:
            return

        # Final deduplication guard: drop any rows with duplicate match_id+player_id
        if "match_id" in df.columns and "player_id" in df.columns:
            df = df.drop_duplicates(subset=["match_id", "player_id"], keep="last")

        self.final_results_cache_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(self.final_results_cache_path, index=False)
