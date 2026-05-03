"""Unified HMM predictor — entry point for the backend."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

from backend.core.hmm.general_hmm import GeneralHMM
from backend.core.hmm.short_term_hmm import ShortTermHMM

logger = logging.getLogger(__name__)

_MIN_SHORT_TERM = 15
_ROLLING_WINDOW = 5
_ROLLING_MIN = 4
_ELO_CLAMP = (0.75, 1.40)


class HMMPredictor:
    """Unified form predictor used by the Flask backend."""

    def __init__(
        self,
        hmm_model_path: Path,
        per_player_dir: Path,
        elo_df: pd.DataFrame,
    ) -> None:
        self._general = GeneralHMM(hmm_model_path)
        self._elo_df = elo_df

        artifact = joblib.load(hmm_model_path)
        role_edges = artifact["obs_bin_edges"]
        default_edges = role_edges.get("All-Rounder", next(iter(role_edges.values())))

        self._short_term = ShortTermHMM(
            models_dir=per_player_dir,
            bin_edges=default_edges,
        )

        elo_col = elo_df["player_elo_post"].dropna()
        self._mean_elo: float = float(elo_col.mean()) if len(elo_col) else 1500.0
        self._std_elo: float = float(elo_col.std()) if len(elo_col) > 1 else 100.0

    def _fetch_latest_elo(self, player_id: str) -> float | None:
        mask = self._elo_df["player_id"] == player_id
        rows = self._elo_df.loc[mask].dropna(subset=["player_elo_post"])
        if rows.empty:
            return None
        if "match_date" in rows.columns:
            rows = rows.sort_values("match_date")
        return float(rows.iloc[-1]["player_elo_post"])

    def _elo_multiplier(self, elo_post: float | None) -> float:
        if elo_post is None:
            return 1.0
        std = self._std_elo if self._std_elo > 1.0 else 100.0
        z = (elo_post - self._mean_elo) / (2.0 * std)
        return float(np.clip(1.0 + z, *_ELO_CLAMP))

    def calibrate_to_pool(self, player_ids: list[str]) -> None:
        """Recompute mean/std from match-pool players only.

        Normalises z-scores relative to the two franchises in the current
        match rather than the entire global dataset, giving elite PSL
        players full multiplier headroom.
        """
        elos: list[float] = []
        for pid in player_ids:
            elo = self._fetch_latest_elo(pid)
            if elo is not None:
                elos.append(elo)
        if len(elos) >= 4:
            arr = np.array(elos, dtype=float)
            self._mean_elo = float(arr.mean())
            self._std_elo = float(arr.std()) if arr.std() > 1.0 else 100.0
            logger.debug(
                "Pool Elo calibration: n=%d mean=%.1f std=%.1f",
                len(elos), self._mean_elo, self._std_elo,
            )

    def _rolling_avg(self, history: list[float]) -> tuple[float | None, int]:
        if len(history) < _ROLLING_MIN:
            return None, 0
        window = min(_ROLLING_WINDOW, len(history))
        avg = float(np.mean(history[-window:]))
        return avg, window

    def predict(self, player_id: str, role: str, history_points: list[float]) -> dict:
        if len(history_points) >= _MIN_SHORT_TERM:
            try:
                hmm_result = self._short_term.predict(player_id, history_points)
            except Exception as exc:
                logger.warning("ShortTermHMM failed for %s: %s; falling back", player_id, exc)
                hmm_result = self._general.predict(role, history_points)
        elif len(history_points) == 0:
            hmm_result = {"state": "unknown", "probs": None, "source": "general"}
        else:
            hmm_result = self._general.predict(role, history_points)

        career_avg: float | None = None
        career_std: float | None = None
        career_variance: float | None = None
        if history_points:
            arr = np.array(history_points, dtype=float)
            career_avg = float(arr.mean())
            career_std = float(arr.std())
            career_variance = float(arr.var())

        rolling_avg, rolling_window = self._rolling_avg(history_points)
        rolling_fallback = rolling_avg is None
        base_score = rolling_avg if rolling_avg is not None else career_avg

        elo_post = self._fetch_latest_elo(player_id)
        elo_multiplier = self._elo_multiplier(elo_post)

        adjusted_score: float | None = None
        if base_score is not None:
            adjusted_score = round(base_score * elo_multiplier, 2)

        return {
            "state": hmm_result.get("state", "unknown"),
            "probs": hmm_result.get("probs"),
            "source": hmm_result.get("source", "general"),
            "career_avg": round(career_avg, 2) if career_avg is not None else None,
            "career_std": round(career_std, 2) if career_std is not None else None,
            "career_variance": round(career_variance, 2) if career_variance is not None else None,
            "matches_in_history": len(history_points),
            "rolling_avg": round(rolling_avg, 2) if rolling_avg is not None else None,
            "rolling_window": rolling_window,
            "rolling_fallback": rolling_fallback,
            "elo_post": round(elo_post, 1) if elo_post is not None else None,
            "elo_multiplier": round(elo_multiplier, 4),
            "adjusted_score": adjusted_score,
        }
