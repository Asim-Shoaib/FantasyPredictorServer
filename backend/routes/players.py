"""Players route — GET /api/players, GET /api/players/<id>/history"""

from __future__ import annotations

import logging
from dataclasses import asdict

import pandas as pd
from flask import Blueprint, jsonify, request

import backend.data_cache as cache
from backend.data_cache import _DATA_DIR, _OUTPUT_DIR, PLAYER_PROFILES_JSON
from backend.services.player_service import build_all_player_profiles, get_player_history
from backend.services.profile_fetcher import ProfileFetcher

logger = logging.getLogger(__name__)

players_bp = Blueprint("players", __name__)

_PEOPLE_CSV = _DATA_DIR / "people.csv"


@players_bp.route("/api/players", methods=["GET"])
def get_players():
    team_a = request.args.get("team_a")
    team_b = request.args.get("team_b")

    profiles = build_all_player_profiles(team_a=team_a, team_b=team_b)
    return jsonify([asdict(p) for p in profiles])


@players_bp.route("/api/players/<player_id>/history", methods=["GET"])
def get_player_history_route(player_id: str):
    history = get_player_history(player_id)
    return jsonify(history)


def _build_identifier_to_cricinfo(people_csv_path) -> dict[str, str]:
    """Return a mapping of Cricsheet identifier → cricinfo ID from people.csv.

    The ELO CSV uses the Cricsheet `identifier` column as player_id (e.g.
    "4acd8fc4").  ESPN API calls need the `key_cricinfo` column.  This function
    produces the bridge so player_profiles.json is keyed by the same IDs that
    player_service.py uses when looking up photo_url.
    """
    if not people_csv_path.exists():
        return {}
    try:
        df = pd.read_csv(people_csv_path, dtype=str, low_memory=False).fillna("")
        if "identifier" not in df.columns or "key_cricinfo" not in df.columns:
            logger.warning(
                "people.csv missing 'identifier' or 'key_cricinfo' column — photos disabled"
            )
            return {}
        result: dict[str, str] = {}
        for _, row in df.iterrows():
            identifier = str(row["identifier"]).strip()
            cricinfo_id = str(row["key_cricinfo"]).strip()
            # Skip rows with no valid data
            if not identifier or not cricinfo_id or cricinfo_id in ("", "nan"):
                continue
            # key_cricinfo is a float in some CSVs — strip the ".0"
            if cricinfo_id.endswith(".0"):
                cricinfo_id = cricinfo_id[:-2]
            result[identifier] = cricinfo_id
        return result
    except Exception as exc:
        logger.error("Failed to read people.csv for photo mapping: %s", exc)
        return {}


@players_bp.route("/api/admin/fetch-photos", methods=["POST"])
def fetch_photos():
    """Fetch ESPN headshots for all roster players and update the cache.

    player_profiles.json is keyed by Cricsheet identifier (same IDs used in the
    ELO CSV and returned by player_service.py) so that photo_url lookups succeed.
    """
    # Step 1: Build identifier → cricinfo_id from people.csv
    identifier_to_cricinfo = _build_identifier_to_cricinfo(_PEOPLE_CSV)
    if not identifier_to_cricinfo:
        return jsonify({"error": "Could not build identifier→cricinfo mapping from people.csv"}), 500

    # Step 2: Also build name → identifier from the ELO CSV so we can resolve
    #         roster player names to their Cricsheet identifiers.
    name_to_identifier: dict[str, str] = {}
    if not cache.elo_df.empty and "player_name" in cache.elo_df.columns and "player_id" in cache.elo_df.columns:
        for pid in cache.elo_df["player_id"].unique():
            rows = cache.elo_df[cache.elo_df["player_id"] == pid]
            if not rows.empty:
                pname = str(rows.iloc[-1]["player_name"]).lower().strip()
                name_to_identifier[pname] = str(pid)

    # Step 3: Build player_map — { cricsheet_identifier: cricinfo_id }
    #         Only include roster players that appear in the ELO CSV.
    player_map: dict[str, str] = {}
    unmapped: list[str] = []

    for player_name in cache.roster:
        key = str(player_name).lower().strip()
        identifier = name_to_identifier.get(key)
        if identifier is None:
            unmapped.append(player_name)
            continue
        cricinfo_id = identifier_to_cricinfo.get(identifier)
        if not cricinfo_id:
            unmapped.append(player_name)
            continue
        player_map[identifier] = cricinfo_id

    if unmapped:
        logger.info(
            "fetch-photos: %d roster players could not be mapped to cricinfo IDs: %s",
            len(unmapped),
            ", ".join(unmapped[:10]) + ("..." if len(unmapped) > 10 else ""),
        )

    if not player_map:
        return jsonify({
            "fetched": 0,
            "with_photo": 0,
            "message": "No players could be mapped to cricinfo IDs",
        })

    # Step 4: Run the fetcher (keyed by Cricsheet identifier)
    fetcher = ProfileFetcher(people_csv=_PEOPLE_CSV, output_path=PLAYER_PROFILES_JSON)
    profiles = fetcher.run(player_ids=player_map)

    # Step 5: Update the in-memory cache
    cache.player_profiles = profiles

    fetched = len(player_map)
    with_photo = sum(
        1 for pid in player_map
        if profiles.get(pid, {}) and profiles[pid].get("photo_url")
    )

    logger.info(
        "fetch-photos: attempted=%d with_photo=%d unmapped=%d",
        fetched, with_photo, len(unmapped),
    )
    return jsonify({
        "fetched": fetched,
        "with_photo": with_photo,
        "unmapped": len(unmapped),
    })


@players_bp.route("/api/admin/photo-status", methods=["GET"])
def photo_status():
    """Return counts of roster players and how many have photos cached.

    Uses Cricsheet identifier keys — the same keys that player_service.py uses
    when looking up photo_url in the in-memory player_profiles dict.
    """
    # Build name → identifier from ELO CSV
    name_to_identifier: dict[str, str] = {}
    if not cache.elo_df.empty and "player_name" in cache.elo_df.columns:
        for pid in cache.elo_df["player_id"].unique():
            rows = cache.elo_df[cache.elo_df["player_id"] == pid]
            if not rows.empty:
                pname = str(rows.iloc[-1]["player_name"]).lower().strip()
                name_to_identifier[pname] = str(pid)

    total = len(cache.roster)
    with_photo = 0
    missing = 0

    for player_name in cache.roster:
        key = str(player_name).lower().strip()
        identifier = name_to_identifier.get(key)
        profile = cache.player_profiles.get(identifier) if identifier else None
        if profile and profile.get("photo_url"):
            with_photo += 1
        else:
            missing += 1

    return jsonify({"total": total, "with_photo": with_photo, "missing": missing})
