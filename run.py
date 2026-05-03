"""
DraftGenius — backend launcher.

Development workflow
--------------------
  Terminal 1 (backend):   python run.py
  Terminal 2 (frontend):  cd frontend && npm run dev

  Backend API:   http://localhost:5000/api/...
  Frontend UI:   http://localhost:5173          (Vite dev server, proxies /api -> :5000)

Optional: run both from one terminal with --with-frontend
  python run.py --with-frontend

Other flags
-----------
  python run.py --port 8080          # custom port
  python run.py --update-data        # pull latest Cricsheet data & rebuild Elo CSV
  python run.py --retrain-models     # delete cached per-player HMM models
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("draftgenius")


# ── argument parsing ───────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Start DraftGenius Flask API backend.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Development usage:\n"
            "  Terminal 1:  python run.py\n"
            "  Terminal 2:  cd frontend && npm run dev\n\n"
            "Or single-terminal:\n"
            "  python run.py --with-frontend\n"
        ),
    )
    p.add_argument("--port", type=int, default=5000, help="Flask port (default: 5000)")
    p.add_argument(
        "--with-frontend",
        action="store_true",
        help="Also launch `npm run dev` in frontend/ alongside the backend.",
    )
    p.add_argument(
        "--update-data",
        action="store_true",
        help="Download latest match data from Cricsheet and rebuild Elo CSV before starting.",
    )
    p.add_argument(
        "--retrain-models",
        action="store_true",
        help="Delete cached per-player HMM models so they are re-fitted on startup.",
    )
    return p.parse_args()


# ── pre-flight steps ───────────────────────────────────────────────────────────

def update_data() -> None:
    """Download latest Cricsheet data and rebuild the Elo CSV."""
    logger.info("Updating match data from Cricsheet…")
    result = subprocess.run(
        [sys.executable, "-m", "backend.cli", "--update-data", "--root-dir", str(ROOT)],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        logger.warning("Data update returned non-zero exit code — continuing anyway.")


def clear_per_player_models() -> None:
    """Remove cached per-player HMM joblib files so they re-fit on next predict."""
    per_player_dir = ROOT / "models" / "per_player"
    if not per_player_dir.exists():
        return
    removed = sum(1 for f in per_player_dir.glob("*.joblib") if f.unlink() is None)
    logger.info("Cleared %d cached per-player HMM models.", removed)


def check_data_files() -> None:
    """Warn about missing critical data files."""
    critical = [
        ROOT / "data" / "all_leagues_player_match_elo.csv",
        ROOT / "models" / "hmm_form_models.joblib",
        ROOT / "data" / "psl_2026_roster_overrides.json",
    ]
    missing = [str(p.relative_to(ROOT)) for p in critical if not p.exists()]
    if missing:
        logger.warning(
            "Missing data files (predictions may be degraded):\n  %s",
            "\n  ".join(missing),
        )


def start_frontend(frontend_dir: Path, backend_port: int) -> "subprocess.Popen[bytes]":
    """Launch `npm run dev` and return the process handle."""
    npm_cmd = (
        shutil.which("npm.cmd") or shutil.which("npm.CMD") or shutil.which("npm")
        if sys.platform == "win32"
        else shutil.which("npm")
    )
    if not npm_cmd:
        logger.error("npm not found in PATH — cannot start frontend dev server.")
        sys.exit(1)

    logger.info("Starting Vite dev server (proxying /api -> http://localhost:%d)…", backend_port)
    proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(frontend_dir),
        shell=False,
    )
    return proc


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    if args.update_data:
        update_data()

    if args.retrain_models:
        clear_per_player_models()

    check_data_files()

    import os
    os.environ["PORT"] = str(args.port)

    # Import here so preflight warnings print before heavy data loads
    from backend.data_cache import init_cache
    from backend.app import create_app

    logger.info("Loading data cache…")
    init_cache()

    app = create_app()

    frontend_proc: "subprocess.Popen[bytes] | None" = None
    if args.with_frontend:
        frontend_dir = ROOT / "frontend"
        if frontend_dir.exists():
            frontend_proc = start_frontend(frontend_dir, args.port)
        else:
            logger.warning("frontend/ directory not found — skipping Vite dev server.")

    logger.info(
        "\n\n"
        "  ✓  DraftGenius backend running at  http://localhost:%d/api/health\n"
        "%s"
        "\n",
        args.port,
        (
            f"  ✓  Frontend dev server at        http://localhost:5173\n"
            if args.with_frontend else
            "     Run `cd frontend && npm run dev` to start the UI (port 5173)\n"
        ),
    )

    try:
        app.run(host="0.0.0.0", port=args.port, debug=False, use_reloader=False)
    finally:
        if frontend_proc is not None:
            logger.info("Shutting down Vite dev server…")
            frontend_proc.terminate()


if __name__ == "__main__":
    main()
