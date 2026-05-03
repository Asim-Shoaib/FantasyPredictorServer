"""Teams route — POST /api/generate-teams, GET /api/evolution/<run_id>"""

from __future__ import annotations

import dataclasses
import json
import queue
import threading
import uuid
from dataclasses import asdict

from flask import Blueprint, Response, jsonify, request, stream_with_context

import backend.data_cache as cache
from backend.services.player_service import build_all_player_profiles
from backend.services.team_generator import GeneticTeamGenerator, TeamConstraints

teams_bp = Blueprint("teams", __name__)

# In-memory evolution store (keyed by run_id)
_evolution_store: dict[str, dict] = {}
_generator = GeneticTeamGenerator()

_run_store: dict[str, dict] = {}
# Each entry: { "status": "running"|"done"|"error", "queue": queue.Queue, "result": dict|None, "error": str|None }


def _run_ga_background(run_id: str, team_a: str, team_b: str, constraints_override: dict) -> None:
    """Runs GA in background thread, putting SSE events into the run's queue."""
    q = _run_store[run_id]["queue"]
    try:
        saved = cache.get_constraints()
        merged = {**saved, **constraints_override, "team_a": team_a, "team_b": team_b}
        constraints = TeamConstraints.from_dict(merged)

        players = build_all_player_profiles(team_a=team_a, team_b=team_b)
        active_players = [p for p in players if p.is_active]

        if len(active_players) < 11:
            q.put(json.dumps({"type": "error", "error": f"Not enough active players: {len(active_players)}"}))
            q.put(None)
            _run_store[run_id]["status"] = "error"
            return

        def progress_callback(strategy: str, generation: int, fitness: float) -> None:
            event = json.dumps({"type": "progress", "strategy": strategy, "generation": generation, "fitness": fitness})
            q.put(event)

        result = _generator.generate(
            players=players,
            constraints=constraints,
            track_evolution=False,
            progress_callback=progress_callback,
        )

        final = {
            "type": "complete",
            "run_id": result.run_id,
            "match": {"team_a": team_a, "team_b": team_b},
            "safe": _team_result_to_dict(result.safe),
            "explosive": _team_result_to_dict(result.explosive),
            "balanced": _team_result_to_dict(result.balanced),
        }
        q.put(json.dumps(final))
        q.put(None)  # sentinel
        _run_store[run_id]["status"] = "done"
        _run_store[run_id]["result"] = final

    except Exception as exc:
        q.put(json.dumps({"type": "error", "error": str(exc)}))
        q.put(None)
        _run_store[run_id]["status"] = "error"
        _run_store[run_id]["error"] = str(exc)


@teams_bp.route("/api/generate-teams-start", methods=["POST"])
def generate_teams_start():
    """Start a GA run in the background. Returns run_id immediately."""
    body = request.get_json(silent=True) or {}
    team_a = body.get("team_a", "")
    team_b = body.get("team_b", "")

    if not team_a or not team_b:
        return jsonify({"error": "team_a and team_b are required"}), 400

    run_id = str(uuid.uuid4().hex[:12])
    q: queue.Queue = queue.Queue()
    _run_store[run_id] = {"status": "running", "queue": q, "result": None, "error": None}

    constraints_override = body.get("constraints", {})
    t = threading.Thread(
        target=_run_ga_background,
        args=(run_id, team_a, team_b, constraints_override),
        daemon=True,
    )
    t.start()

    return jsonify({"run_id": run_id})


@teams_bp.route("/api/stream/<run_id>", methods=["GET"])
def stream_evolution_sse(run_id: str):
    """SSE endpoint — streams GA progress and final result for a run."""
    if run_id not in _run_store:
        return jsonify({"error": "Unknown run_id"}), 404

    def event_stream():
        q = _run_store[run_id]["queue"]
        while True:
            try:
                item = q.get(timeout=120)  # 2-min timeout
            except queue.Empty:
                yield "data: " + json.dumps({"type": "error", "error": "timeout"}) + "\n\n"
                return

            if item is None:
                return  # sentinel — GA finished

            yield "data: " + item + "\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@teams_bp.route("/api/generate-teams", methods=["POST"])
def generate_teams():
    body = request.get_json(silent=True) or {}

    team_a = body.get("team_a", "")
    team_b = body.get("team_b", "")

    if not team_a or not team_b:
        return jsonify({"error": "team_a and team_b are required"}), 400

    # Load saved constraints, then apply any overrides from request body
    saved = cache.get_constraints()
    constraint_overrides = body.get("constraints", {})
    merged = {**saved, **constraint_overrides, "team_a": team_a, "team_b": team_b}
    constraints = TeamConstraints.from_dict(merged)

    # Build player pool for these two teams only
    players = build_all_player_profiles(team_a=team_a, team_b=team_b)
    active_players = [p for p in players if p.is_active]

    if len(active_players) < 11:
        return jsonify({
            "error": "Not enough active players",
            "active_count": len(active_players),
        }), 400

    track_evolution = body.get("track_evolution", False)

    try:
        result = _generator.generate(
            players=players,
            constraints=constraints,
            track_evolution=track_evolution,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if track_evolution and result.evolution:
        _evolution_store[result.run_id] = result.evolution

    def team_to_dict(t):
        d = asdict(t) if dataclasses.is_dataclass(t) else t.__dict__
        return d

    return jsonify({
        "run_id": result.run_id,
        "match": {"team_a": team_a, "team_b": team_b},
        "safe": _team_result_to_dict(result.safe),
        "explosive": _team_result_to_dict(result.explosive),
        "balanced": _team_result_to_dict(result.balanced),
        "evolution_available": bool(result.evolution),
    })


def _team_result_to_dict(t) -> dict:
    return {
        "strategy": t.strategy,
        "players": t.players,
        "captain": t.captain,
        "vc": t.vc,
        "total_credits": t.total_credits,
        "fitness": t.fitness,
        "expected_score": getattr(t, "expected_score", 0.0),
        "ceiling_score": getattr(t, "ceiling_score", 0.0),
        "floor_score": getattr(t, "floor_score", 0.0),
        "team_rolling_avg": t.team_rolling_avg,
        "team_career_std": t.team_career_std,
        "team_hot_prob": getattr(t, "team_hot_prob", 0.0),
    }


@teams_bp.route("/api/evolution/<run_id>", methods=["GET"])
def get_evolution(run_id: str):
    if run_id not in _evolution_store:
        return jsonify({"error": "Evolution data not found for this run"}), 404
    return jsonify(_evolution_store[run_id])
