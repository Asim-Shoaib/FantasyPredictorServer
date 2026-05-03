"""Players route — GET /api/players, GET /api/players/<id>/history"""

from __future__ import annotations

import json
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


def _build_people_indexes(people_csv_path) -> tuple[dict[str, dict], dict[str, list]]:
    """Return (exact_by_name, by_lastname) indexes from people.csv.

    exact_by_name: name.lower() → {identifier, key_cricinfo}
    by_lastname:   last_word.lower() → list of {identifier, key_cricinfo, first_initial}

    people.csv uses initials (e.g. "DA Warner") rather than full first names,
    so we index by last name and first initial to resolve full-name roster entries.
    """
    if not people_csv_path.exists():
        return {}, {}
    try:
        df = pd.read_csv(people_csv_path, dtype=str, low_memory=False).fillna("")
        required = {"identifier", "name", "key_cricinfo"}
        if not required.issubset(df.columns):
            return {}, {}
        exact: dict[str, dict] = {}
        by_last: dict[str, list] = {}
        for _, row in df.iterrows():
            name = str(row["name"]).strip()
            identifier = str(row["identifier"]).strip()
            cid = str(row["key_cricinfo"]).strip()
            if not name or not identifier or cid in ("", "nan"):
                continue
            if cid.endswith(".0"):
                cid = cid[:-2]
            entry = {"identifier": identifier, "key_cricinfo": cid}
            exact[name.lower()] = entry
            parts = name.lower().split()
            if parts:
                last = parts[-1]
                first_initial = parts[0][0]
                by_last.setdefault(last, []).append({**entry, "first_initial": first_initial})
        return exact, by_last
    except Exception as exc:
        logger.error("Failed to build people.csv indexes: %s", exc)
        return {}, {}


def _resolve_roster_name(name: str, exact: dict, by_last: dict) -> dict | None:
    """Resolve a full roster player name to a people.csv entry.

    1. Exact lowercase match.
    2. Last name + first initial match (unambiguous only).
    """
    key = name.lower().strip()
    if key in exact:
        return exact[key]
    parts = key.split()
    if not parts:
        return None
    last = parts[-1].rstrip(".")  # strip trailing dot (e.g. "Jr.")
    first_initial = parts[0][0]
    candidates = [c for c in by_last.get(last, []) if c["first_initial"] == first_initial]
    if len(candidates) == 1:
        return candidates[0]
    return None


@players_bp.route("/api/admin/fetch-photos", methods=["POST"])
def fetch_photos():
    """Fetch ESPN headshots for all roster players and update the cache.

    player_profiles.json is keyed by Cricsheet identifier (same IDs used in the
    ELO CSV and returned by player_service.py) so that photo_url lookups succeed.
    Works with or without the ELO CSV — falls back to matching roster names
    directly against people.csv when ELO data is unavailable.
    """
    # Step 1: Build people.csv indexes
    exact, by_last = _build_people_indexes(_PEOPLE_CSV)
    if not exact:
        return jsonify({"error": "Could not read people.csv — check data/people.csv exists"}), 500

    # Step 2: Build player_map — { cricsheet_identifier: cricinfo_id }
    player_map: dict[str, str] = {}
    unmapped: list[str] = []

    for player_name in cache.roster:
        entry = _resolve_roster_name(str(player_name), exact, by_last)
        if entry:
            player_map[entry["identifier"]] = entry["key_cricinfo"]
        else:
            unmapped.append(player_name)

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
    """Return counts of profiles saved to disk and how many have photo URLs."""
    profiles: dict = {}
    if PLAYER_PROFILES_JSON.exists():
        try:
            with PLAYER_PROFILES_JSON.open(encoding="utf-8") as f:
                profiles = json.load(f)
        except Exception:
            pass

    total = len(profiles)
    with_photo = sum(1 for p in profiles.values() if p.get("photo_url"))
    return jsonify({"total": total, "with_photo": with_photo, "missing": total - with_photo})
