"""Constraints route — GET/POST /api/constraints"""

from __future__ import annotations

import dataclasses

from flask import Blueprint, jsonify, request

import backend.data_cache as cache
from backend.services.team_generator import TeamConstraints

constraints_bp = Blueprint("constraints", __name__)


@constraints_bp.route("/api/constraints", methods=["GET"])
def get_constraints():
    saved = cache.get_constraints()
    defaults = dataclasses.asdict(TeamConstraints())
    # Merge saved over defaults
    merged = {**defaults, **saved}
    return jsonify(merged)


@constraints_bp.route("/api/constraints", methods=["POST"])
def update_constraints():
    body = request.get_json(silent=True) or {}
    saved = cache.get_constraints()
    merged = {**saved, **body}
    cache.save_constraints(merged)
    return jsonify(merged)
