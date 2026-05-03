"""Player service — builds PlayerProfile objects from ELO CSV + caches."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd

import backend.data_cache as cache
from backend.services.credit_engine import CreditEngine

logger = logging.getLogger(__name__)


@dataclass
class PlayerProfile:
    player_id: str
    player_name: str
    team: str
    role: str
    credits: float
    is_active: bool

    # HMM / form
    form_state: str = "unknown"
    form_probs: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    form_source: str = "general"

    # Score fields
    career_avg: float | None = None
    career_std: float | None = None
    career_variance: float | None = None
    rolling_avg: float | None = None
    rolling_window: int = 0
    rolling_fallback: bool = False
    adjusted_score: float | None = None
    elo_post: float | None = None
    elo_multiplier: float = 1.0
    matches_in_history: int = 0

    # Media
    photo_url: str | None = None


def _get_team_for_player(player_name: str) -> str:
    """Lookup team name from roster JSON."""
    entry = cache.roster.get(player_name)
    if entry is None:
        return ""
    if isinstance(entry, dict):
        return entry.get("team", "")
    return str(entry)


def _get_history_points(player_id: str) -> list[float]:
    """Return chronological fantasy_points for a player."""
    if cache.elo_df.empty:
        return []
    mask = cache.elo_df["player_id"] == player_id
    rows = cache.elo_df.loc[mask].copy()
    if rows.empty:
        return []
    if "match_date" in rows.columns:
        rows["match_date"] = pd.to_datetime(rows["match_date"], errors="coerce")
        rows = rows.sort_values("match_date")
    return rows["fantasy_points"].fillna(0).tolist()


def build_all_player_profiles(
    team_a: str | None = None,
    team_b: str | None = None,
) -> list[PlayerProfile]:
    """Build PlayerProfile list, optionally filtered to two franchises.

    Parameters
    ----------
    team_a, team_b:
        If provided, only players from these two franchises are returned.
        This is the single-match mode — pool is exactly 2 teams.
    """
    credit_engine = CreditEngine(overrides=cache.credits_override)

    # Build name→profile mapping from roster
    # roster: {player_name: {team, ...} or team_string}
    profiles: list[PlayerProfile] = []

    # Determine all player_ids present in ELO CSV
    if cache.elo_df.empty:
        logger.warning("ELO CSV empty — returning empty player list")
        return []

    all_ids = cache.elo_df["player_id"].unique()

    # Build a name→id mapping from the CSV
    name_id_map: dict[str, str] = {}
    if "player_name" in cache.elo_df.columns:
        for pid in all_ids:
            rows = cache.elo_df[cache.elo_df["player_id"] == pid]
            if not rows.empty:
                name_id_map[rows.iloc[-1]["player_name"]] = pid

    # Calibrate Elo distribution to match pool (2-franchise z-score baseline)
    if cache.hmm_predictor and (team_a and team_b):
        pool_ids: list[str] = []
        for pname, pentry in cache.roster.items():
            pteam = pentry.get("team", "") if isinstance(pentry, dict) else str(pentry)
            if pteam not in (team_a, team_b):
                continue
            pid = name_id_map.get(pname)
            if pid is None:
                ms = [p for n, p in name_id_map.items() if pname.lower() in n.lower()]
                pid = ms[0] if ms else pname.lower().replace(" ", "-")
            pool_ids.append(pid)
        cache.hmm_predictor.calibrate_to_pool(pool_ids)

    # Collect all avgs for credit percentile computation
    all_avgs: list[float] = []

    player_data: list[dict] = []

    for player_name, entry in cache.roster.items():
        team = entry.get("team", "") if isinstance(entry, dict) else str(entry)

        # Filter to match teams if specified
        if team_a and team_b:
            if team not in (team_a, team_b):
                continue

        player_id = name_id_map.get(player_name)
        if player_id is None:
            # Try fuzzy match by checking ELO CSV player names
            matches = [pid for n, pid in name_id_map.items() if player_name.lower() in n.lower()]
            player_id = matches[0] if matches else player_name.lower().replace(" ", "-")

        role = cache.role_cache.get(player_id, "All-Rounder")
        history = _get_history_points(player_id)

        # HMM prediction
        hmm_result: dict = {}
        if cache.hmm_predictor and history:
            try:
                hmm_result = cache.hmm_predictor.predict(player_id, role, history)
            except Exception as exc:
                logger.warning("HMM predict failed for %s: %s", player_id, exc)

        career_avg = hmm_result.get("career_avg")
        rolling_avg = hmm_result.get("rolling_avg")
        base_avg = rolling_avg if rolling_avg is not None else career_avg
        if base_avg is not None:
            all_avgs.append(base_avg)

        player_data.append({
            "player_id": player_id,
            "player_name": player_name,
            "team": team,
            "role": role,
            "history": history,
            "hmm_result": hmm_result,
            "career_avg": career_avg,
            "rolling_avg": rolling_avg,
            "base_avg": base_avg,
        })

    # Second pass: compute credits with full pool percentile context
    for pd_entry in player_data:
        player_id = pd_entry["player_id"]
        hmm_result = pd_entry["hmm_result"]
        elo_mult = hmm_result.get("elo_multiplier", 1.0)

        credits = credit_engine.compute(
            player_id=player_id,
            rolling_avg=pd_entry["rolling_avg"],
            career_avg=pd_entry["career_avg"],
            elo_multiplier=elo_mult,
            all_avgs=all_avgs,
        )

        is_active = not cache.active_overrides.get(player_id, {}).get("benched", False)
        photo_url = cache.player_profiles.get(player_id, {}).get("photo_url")

        profile = PlayerProfile(
            player_id=player_id,
            player_name=pd_entry["player_name"],
            team=pd_entry["team"],
            role=pd_entry["role"],
            credits=credits,
            is_active=is_active,
            form_state=hmm_result.get("state", "unknown"),
            form_probs=hmm_result.get("probs") or [0.0, 0.0, 0.0],
            form_source=hmm_result.get("source", "general"),
            career_avg=pd_entry["career_avg"],
            career_std=hmm_result.get("career_std"),
            career_variance=hmm_result.get("career_variance"),
            rolling_avg=pd_entry["rolling_avg"],
            rolling_window=hmm_result.get("rolling_window", 0),
            rolling_fallback=hmm_result.get("rolling_fallback", False),
            adjusted_score=hmm_result.get("adjusted_score"),
            elo_post=hmm_result.get("elo_post"),
            elo_multiplier=elo_mult,
            matches_in_history=len(pd_entry["history"]),
            photo_url=photo_url,
        )
        profiles.append(profile)

    return profiles


def get_player_history(player_id: str) -> list[dict]:
    """Return last 20 match records for a player."""
    if cache.elo_df.empty:
        return []
    mask = cache.elo_df["player_id"] == player_id
    rows = cache.elo_df.loc[mask].copy()
    if rows.empty:
        return []

    cols = [
        "match_date", "opposition", "fantasy_points",
        "batting_points", "bowling_points", "fielding_points",
        "player_elo_post",
    ]
    available = [c for c in cols if c in rows.columns]
    rows = rows.sort_values("match_date", ascending=False).head(20)[available]

    # Add rolling avg at each match point
    records = rows.to_dict(orient="records")
    return records
