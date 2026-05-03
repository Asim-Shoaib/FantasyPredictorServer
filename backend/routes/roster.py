"""Roster route — bench / reinstate players."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

import backend.data_cache as cache

roster_bp = Blueprint("roster", __name__)


@roster_bp.route("/api/roster/bench/<player_id>", methods=["POST"])
def bench_player(player_id: str):
    overrides = dict(cache.active_overrides)
    overrides.setdefault(player_id, {})["benched"] = True
    cache.save_active_overrides(overrides)
    return jsonify({"player_id": player_id, "benched": True})


@roster_bp.route("/api/roster/reinstate/<player_id>", methods=["POST"])
def reinstate_player(player_id: str):
    overrides = dict(cache.active_overrides)
    if player_id in overrides:
        overrides[player_id]["benched"] = False
    cache.save_active_overrides(overrides)
    return jsonify({"player_id": player_id, "benched": False})


@roster_bp.route("/api/roster/status", methods=["GET"])
def get_roster_status():
    """Return all bench overrides."""
    return jsonify(cache.active_overrides)
