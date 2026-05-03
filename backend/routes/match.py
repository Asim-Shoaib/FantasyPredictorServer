"""Match route — GET /api/match/teams"""

from __future__ import annotations

from flask import Blueprint, jsonify

import backend.data_cache as cache

match_bp = Blueprint("match", __name__)


@match_bp.route("/api/match/teams", methods=["GET"])
def get_franchise_list():
    """Return sorted list of available PSL franchise names."""
    return jsonify(cache.get_franchise_list())
