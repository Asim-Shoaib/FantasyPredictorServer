"""Backend data cache — loaded once at app startup."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Resolved paths
# -----------------------------------------------------------------------
_ROOT = Path(__file__).parent.parent.resolve()
_DATA_DIR = _ROOT / "data"
_MODELS_DIR = _ROOT / "models"
_OUTPUT_DIR = _DATA_DIR / "output"
_PER_PLAYER_DIR = _MODELS_DIR / "per_player"

ELO_CSV = _DATA_DIR / "all_leagues_player_match_elo.csv"       # moved from root
HMM_MODEL_PATH = _MODELS_DIR / "hmm_form_models.joblib"
ROSTER_JSON = _DATA_DIR / "psl_2026_roster_overrides.json"
ROLE_CACHE_JSON = _OUTPUT_DIR / "role_cache.json"              # moved from root
PLAYER_PROFILES_JSON = _OUTPUT_DIR / "player_profiles.json"
CREDITS_OVERRIDE_JSON = _DATA_DIR / "credits_override.json"
ACTIVE_OVERRIDES_JSON = _DATA_DIR / "active_overrides.json"
CONSTRAINTS_JSON = _DATA_DIR / "constraints.json"

# -----------------------------------------------------------------------
# Module-level singletons (populated by init_cache)
# -----------------------------------------------------------------------
elo_df: pd.DataFrame = pd.DataFrame()
roster: dict = {}          # player_name → team
role_cache: dict = {}      # player_id → role
player_profiles: dict = {} # player_id → {photo_url, ...}
credits_override: dict = {}
active_overrides: dict = {}
hmm_predictor = None       # HMMPredictor instance


def init_cache() -> None:
    """Load all data files into module-level singletons."""
    global elo_df, roster, role_cache, player_profiles, credits_override, active_overrides, hmm_predictor

    logger.info("Loading ELO CSV from %s ...", ELO_CSV)
    if ELO_CSV.exists():
        elo_df = pd.read_csv(ELO_CSV, low_memory=False)
        logger.info("ELO CSV loaded: %d rows", len(elo_df))
    else:
        logger.warning("ELO CSV not found at %s", ELO_CSV)
        elo_df = pd.DataFrame()

    roster = _load_json(ROSTER_JSON)
    role_cache = _load_json(ROLE_CACHE_JSON)
    player_profiles = _load_json(PLAYER_PROFILES_JSON)
    profiles_with_photo = sum(
        1 for p in player_profiles.values() if isinstance(p, dict) and p.get("photo_url")
    )
    logger.info(
        "Player profiles loaded: %d total, %d with photo_url",
        len(player_profiles),
        profiles_with_photo,
    )
    credits_override = _load_json(CREDITS_OVERRIDE_JSON)
    active_overrides = _load_json(ACTIVE_OVERRIDES_JSON)

    _PER_PLAYER_DIR.mkdir(parents=True, exist_ok=True)

    if HMM_MODEL_PATH.exists() and not elo_df.empty:
        from backend.core.hmm.predictor import HMMPredictor
        hmm_predictor = HMMPredictor(
            hmm_model_path=HMM_MODEL_PATH,
            per_player_dir=_PER_PLAYER_DIR,
            elo_df=elo_df,
        )
        logger.info("HMMPredictor initialised")
    else:
        logger.warning("HMMPredictor not initialised — missing model or ELO data")


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.error("Failed to load %s: %s", path, exc)
        return {}


def get_constraints() -> dict:
    """Load saved constraints from disk (or return empty dict)."""
    return _load_json(CONSTRAINTS_JSON)


def save_constraints(data: dict) -> None:
    """Persist constraint settings to disk."""
    CONSTRAINTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with CONSTRAINTS_JSON.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def save_active_overrides(data: dict) -> None:
    global active_overrides
    active_overrides = data
    ACTIVE_OVERRIDES_JSON.parent.mkdir(parents=True, exist_ok=True)
    with ACTIVE_OVERRIDES_JSON.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_franchise_list() -> list[str]:
    """Return sorted list of unique PSL franchise names."""
    teams = set()
    for entry in roster.values():
        if isinstance(entry, dict):
            team = entry.get("team", "")
        else:
            team = str(entry)
        if team:
            teams.add(team)
    return sorted(teams)
