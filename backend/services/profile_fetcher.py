"""ESPN profile fetcher — caches player headshots and bios."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

import aiohttp
import pandas as pd

logger = logging.getLogger(__name__)

ESPN_API_URL = "https://site.web.api.espn.com/apis/common/v3/sports/cricket/athletes/{cricinfo_id}"
DEFAULT_OUTPUT = Path("data/output/player_profiles.json")
REQUEST_DELAY = 0.05


class ProfileFetcher:
    """Fetch and cache ESPN player profiles (headshots + bio)."""

    def __init__(
        self,
        people_csv: Path,
        output_path: Path = DEFAULT_OUTPUT,
        request_delay: float = REQUEST_DELAY,
    ) -> None:
        self.people_csv = Path(people_csv)
        self.output_path = Path(output_path)
        self.request_delay = request_delay

    def _load_existing(self) -> dict[str, Any]:
        if not self.output_path.exists():
            return {}
        try:
            with self.output_path.open(encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, profiles: dict[str, Any]) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=2, ensure_ascii=False)
        logger.info("Saved %d profiles to %s", len(profiles), self.output_path)

    async def _fetch_one(
        self, session: aiohttp.ClientSession, player_id: str, cricinfo_id: str
    ) -> tuple[str, dict | None]:
        url = ESPN_API_URL.format(cricinfo_id=cricinfo_id)
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return player_id, None
                data = await resp.json(content_type=None)
                athlete = data.get("athlete", {})
                headshot = athlete.get("headshot", {})
                return player_id, {
                    "photo_url": headshot.get("href"),
                    "date_of_birth": athlete.get("dateOfBirth"),
                    "citizenship": athlete.get("citizenship"),
                    "espn_id": str(cricinfo_id),
                }
        except Exception as exc:
            logger.debug("Failed to fetch profile for %s: %s", player_id, exc)
            return player_id, None

    async def _fetch_all(
        self, player_map: dict[str, str], existing: dict[str, Any]
    ) -> dict[str, Any]:
        missing = {pid: cid for pid, cid in player_map.items() if pid not in existing}
        logger.info("Fetching %d new profiles (skipping %d cached)...", len(missing), len(existing))

        profiles = dict(existing)
        async with aiohttp.ClientSession() as session:
            for player_id, cricinfo_id in missing.items():
                pid, result = await self._fetch_one(session, player_id, cricinfo_id)
                if result:
                    profiles[pid] = result
                await asyncio.sleep(self.request_delay)

        return profiles

    def run(self, player_ids: dict[str, str] | None = None) -> dict[str, Any]:
        if player_ids is None:
            player_ids = self._load_from_people_csv()

        existing = self._load_existing()
        profiles = asyncio.run(self._fetch_all(player_ids, existing))
        self._save(profiles)
        return profiles

    def _load_from_people_csv(self) -> dict[str, str]:
        if not self.people_csv.exists():
            logger.warning("people.csv not found at %s", self.people_csv)
            return {}
        df = pd.read_csv(self.people_csv, low_memory=False)
        result: dict[str, str] = {}
        id_col = "key_cricinfo" if "key_cricinfo" in df.columns else None
        name_col = "name" if "name" in df.columns else df.columns[0]
        if id_col is None:
            logger.warning("key_cricinfo column not found in people.csv")
            return {}
        for _, row in df.iterrows():
            cid = row.get(id_col)
            name = row.get(name_col, "")
            if pd.isna(cid) or pd.isna(name):
                continue
            pid = str(name).lower().strip().replace(" ", "-")
            result[pid] = str(int(cid))
        return result


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Fetch ESPN player profiles")
    parser.add_argument("--people-csv", default="people.csv")
    parser.add_argument("--output", default="data/output/player_profiles.json")
    args = parser.parse_args()
    fetcher = ProfileFetcher(Path(args.people_csv), Path(args.output))
    profiles = fetcher.run()
    print(f"Done. {len(profiles)} profiles saved.")
