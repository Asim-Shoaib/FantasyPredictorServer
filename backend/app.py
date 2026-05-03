"""Flask application — serves only API routes.

The React frontend is served by the Vite dev server (npm run dev, port 5173).
Vite proxies all /api/* requests to this Flask server at port 5000.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS

from backend.data_cache import init_cache
from backend.routes.players import players_bp
from backend.routes.teams import teams_bp
from backend.routes.roster import roster_bp
from backend.routes.constraints import constraints_bp
from backend.routes.match import match_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    # No static_folder — assets are served by the Vite dev server
    app = Flask(__name__)

    # Allow requests from the Vite dev server origin.
    # In production you would lock this down to your actual domain.
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # ── API blueprints ────────────────────────────────────────────────────
    app.register_blueprint(players_bp)
    app.register_blueprint(teams_bp)
    app.register_blueprint(roster_bp)
    app.register_blueprint(constraints_bp)
    app.register_blueprint(match_bp)

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "version": "1.0.0"})

    return app


def main() -> None:
    logger.info("Initialising DraftGenius data cache…")
    init_cache()
    port = int(os.environ.get("PORT", 5000))
    logger.info("Starting DraftGenius API on http://localhost:%d", port)
    app = create_app()
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
