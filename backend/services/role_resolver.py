from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
from tqdm import tqdm


class PlayerRoleResolver:
    def __init__(
        self,
        people_csv_path: Path,
        role_cache_path: Path,
        request_delay_seconds: float = 0.02,
    ) -> None:
        self.people_csv_path = people_csv_path
        self.role_cache_path = role_cache_path
        self.request_delay_seconds = request_delay_seconds

        self.people_df = pd.read_csv(people_csv_path, dtype=str).fillna("")
        self.people_by_identifier = {
            row["identifier"]: row for _, row in self.people_df.iterrows()
        }

        self.role_cache: dict[str, str] = {}
        if role_cache_path.exists():
            with role_cache_path.open("r", encoding="utf-8") as f:
                self.role_cache = json.load(f)

    def save_cache(self) -> None:
        self.role_cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.role_cache_path.open("w", encoding="utf-8") as f:
            json.dump(self.role_cache, f, indent=2)

    def infer_role_from_stats(self, batting_avg: float, bowling_avg: float, fielding_avg: float) -> str:
        max_avg = max(batting_avg, bowling_avg, fielding_avg, 1.0)
        batting_norm = (batting_avg / max_avg) * 100 if max_avg > 0 else 0
        bowling_norm = (bowling_avg / max_avg) * 100 if max_avg > 0 else 0
        fielding_norm = (fielding_avg / max_avg) * 100 if max_avg > 0 else 0

        if bowling_norm < 40 and fielding_norm > 60 and batting_norm < 50:
            return "Wicket-Keeper"
        if batting_norm > 70 and fielding_norm > 50 and bowling_norm < 30:
            return "Wicket-Keeper"
        if bowling_norm > 70 and batting_norm < 50:
            return "Bowler"
        if batting_norm > 70 and bowling_norm < 50:
            return "Batter"
        if batting_avg > 0 and bowling_avg > 0:
            return "All-Rounder"
        if batting_avg > bowling_avg and batting_avg > fielding_avg:
            return "Batter"
        if bowling_avg > batting_avg and bowling_avg > fielding_avg:
            return "Bowler"
        return "All-Rounder"

    def _get_cached_role(self, player_id: str) -> str:
        role = self.role_cache.get(player_id, "")
        normalized = str(role or "").strip()
        if not normalized:
            return ""
        return normalized

    def _get_cricinfo_id(self, player_id: str) -> str:
        person_row = self.people_by_identifier.get(player_id)
        if person_row is None:
            return ""
        return str(person_row.get("key_cricinfo", "")).strip()

    async def resolve_roles_bulk(self, players: dict[str, str]) -> dict[str, str]:
        resolved: dict[str, str] = {}
        to_fetch: list[tuple[str, str]] = []

        for player_id in players:
            cached = self._get_cached_role(player_id)
            if cached:
                resolved[player_id] = cached
                continue

            cricinfo_id = self._get_cricinfo_id(player_id)
            if not cricinfo_id:
                self.role_cache[player_id] = "Unknown"
                resolved[player_id] = "Unknown"
                continue

            to_fetch.append((player_id, cricinfo_id))

        semaphore = asyncio.Semaphore(25)

        async def fetch_one(player_id: str, cricinfo_id: str) -> tuple[str, str]:
            async with semaphore:
                if self.request_delay_seconds > 0:
                    await asyncio.sleep(self.request_delay_seconds)
                role = await asyncio.to_thread(self._fetch_role_from_espn, cricinfo_id)
                if not role:
                    role = "Unknown"
                return player_id, role

        tasks = [
            asyncio.create_task(fetch_one(player_id, cricinfo_id))
            for player_id, cricinfo_id in to_fetch
        ]

        if tasks:
            for task in tqdm(
                asyncio.as_completed(tasks),
                total=len(tasks),
                desc="Resolving player roles",
                unit="player",
            ):
                player_id, role = await task
                self.role_cache[player_id] = role
                resolved[player_id] = role

        return resolved

    def _fetch_role_from_espn(self, cricinfo_id: str) -> str:
        url = f"https://site.web.api.espn.com/apis/common/v3/sports/cricket/athletes/{cricinfo_id}"
        payload = self._safe_get_json(url)
        if not payload:
            return ""
        return self._extract_role_from_payload(payload)

    def _safe_get_json(self, url: str) -> dict[str, Any] | None:
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=8) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            return None

    def _extract_role_from_payload(self, payload: dict[str, Any]) -> str:
        if not isinstance(payload, dict):
            return ""

        athlete = payload.get("athlete", {})
        position = athlete.get("position", {})

        if not position:
            return ""

        name_val = str(position.get("name", "") or "").strip()
        abbr_val = str(position.get("abbreviation", "") or "").strip()

        if name_val:
            role = self._map_role_tokens([name_val])
            if role:
                return role
        if abbr_val:
            role = self._map_role_tokens([abbr_val])
            if role:
                return role
        if name_val or abbr_val:
            role = self._map_role_tokens([name_val, abbr_val])
            if role:
                return role
        return ""

    def _map_role_tokens(self, tokens: list[str]) -> str:
        merged = " ".join([t for t in tokens if t]).lower()
        compact = re.sub(r"[^a-z0-9]+", " ", merged).strip()
        token_set = set(compact.split())

        if token_set & {"wbt", "wk", "wkb"}:
            return "Wicket-Keeper"
        if token_set & {"ar", "bla", "bar"}:
            return "All-Rounder"
        if token_set & {"bl", "bof", "bom"}:
            return "Bowler"
        if token_set & {"bt", "obt", "mbt", "tbt"}:
            return "Batter"

        if any(k in compact for k in ["wicketkeeper", "wicket keeper", "keeper"]):
            return "Wicket-Keeper"
        if any(k in compact for k in ["allrounder", "all rounder", "batting allrounder", "bowling allrounder"]):
            return "All-Rounder"
        if any(k in compact for k in ["bowler", "offbreak", "legbreak", "fast", "medium"]):
            return "Bowler"
        if any(k in compact for k in ["batter", "bat", "top order", "middle order", "opening batter"]):
            return "Batter"

        return ""
