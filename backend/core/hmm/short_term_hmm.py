"""Per-player HMM fitted on entire career, persisted to disk."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import joblib
from hmmlearn import hmm

logger = logging.getLogger(__name__)

_MIN_MATCHES = 15
_N_COMPONENTS = 3
_N_RESTARTS = 5
_RECENT_WINDOW = 15
_RETRAIN_THRESHOLD = 10   # re-fit when player accumulates this many new matches since training
_STATE_NAMES = ["cold", "avg", "hot"]


class _StaleModelSignal(Exception):
    """Internal sentinel raised when a per-player model needs re-fitting."""



class ShortTermHMM:
    """Per-player HMM persisted to disk."""

    def __init__(self, models_dir: Path, bin_edges: np.ndarray) -> None:
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.bin_edges = bin_edges

    def _model_path(self, player_id: str) -> Path:
        safe = player_id.replace("/", "_").replace("\\", "_")
        return self.models_dir / f"{safe}.joblib"

    def _discretize(self, points: list[float]) -> np.ndarray:
        bins = np.digitize(points, self.bin_edges) - 1
        return np.clip(bins, 0, _N_COMPONENTS - 1).reshape(-1, 1)

    def _sort_states(self, model: hmm.CategoricalHMM) -> dict[int, str]:
        top_bin_probs = model.emissionprob_[:, -1]
        sorted_indices = np.argsort(top_bin_probs)
        return {int(sorted_indices[i]): _STATE_NAMES[i] for i in range(_N_COMPONENTS)}

    def _fit(self, obs: np.ndarray) -> hmm.CategoricalHMM:
        best_model = None
        best_score = -np.inf

        for _ in range(_N_RESTARTS):
            model = hmm.CategoricalHMM(
                n_components=_N_COMPONENTS,
                n_iter=100,
                tol=1e-4,
                init_params="ste",
                params="ste",
            )
            try:
                model.fit(obs)
                score = model.score(obs)
                if score > best_score:
                    best_score = score
                    best_model = model
            except Exception:
                continue

        if best_model is None:
            raise RuntimeError("All HMM restarts failed.")
        return best_model

    def predict(self, player_id: str, history_points: list[float]) -> dict:
        if len(history_points) < _MIN_MATCHES:
            raise ValueError(
                f"ShortTermHMM requires >= {_MIN_MATCHES} matches; got {len(history_points)}"
            )

        obs_full = self._discretize(history_points)
        model_path = self._model_path(player_id)

        if model_path.exists():
            try:
                saved = joblib.load(model_path)
                # Support both old format (model, state_map) and new format
                # (model, state_map, fitted_on_n_matches).
                if len(saved) == 3:
                    model, state_map, fitted_n = saved
                else:
                    model, state_map = saved
                    fitted_n = len(history_points)  # assume current — no auto-retrain for old files

                new_matches = len(history_points) - fitted_n
                if new_matches >= _RETRAIN_THRESHOLD:
                    logger.debug(
                        "Per-player model for %s is stale (%d new matches since training); re-fitting.",
                        player_id,
                        new_matches,
                    )
                    model_path.unlink(missing_ok=True)
                    raise _StaleModelSignal()

                logger.debug("Loaded per-player model for %s from disk", player_id)
            except _StaleModelSignal:
                model = self._fit(obs_full)
                state_map = self._sort_states(model)
                joblib.dump((model, state_map, len(history_points)), model_path)
            except Exception as exc:
                logger.warning("Corrupt model file for %s (%s); re-fitting...", player_id, exc)
                model_path.unlink(missing_ok=True)
                model = self._fit(obs_full)
                state_map = self._sort_states(model)
                joblib.dump((model, state_map, len(history_points)), model_path)
        else:
            model = self._fit(obs_full)
            state_map = self._sort_states(model)
            joblib.dump((model, state_map, len(history_points)), model_path)
            logger.debug("Saved per-player model for %s", player_id)

        _, state_seq = model.decode(obs_full, algorithm="viterbi")
        current_idx = state_seq[-1]
        state_name = state_map[current_idx]
        trans_row = model.transmat_[current_idx]
        probs = self._build_probs(trans_row, state_map)

        windowed_state, windowed_probs = None, None
        recent = history_points[-_RECENT_WINDOW:]
        if len(recent) >= 3:
            obs_recent = self._discretize(recent)
            _, win_seq = model.decode(obs_recent, algorithm="viterbi")
            win_idx = win_seq[-1]
            windowed_state = state_map[win_idx]
            windowed_probs = self._build_probs(model.transmat_[win_idx], state_map)

        return {
            "state": state_name,
            "probs": probs,
            "source": "short_term",
            "windowed_state": windowed_state,
            "windowed_probs": windowed_probs,
        }

    def _build_probs(self, trans_row: np.ndarray, state_map: dict) -> list[float]:
        named = {state_map[i]: float(trans_row[i]) for i in range(len(trans_row))}
        return [named.get("cold", 0.0), named.get("avg", 0.0), named.get("hot", 0.0)]
