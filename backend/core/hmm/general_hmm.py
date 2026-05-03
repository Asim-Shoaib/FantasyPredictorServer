"""General (role-level) HMM — wraps the pre-trained models/hmm_form_models.joblib."""

from __future__ import annotations

import numpy as np
import joblib
from pathlib import Path


_ROLE_ALIASES: dict[str, str] = {
    "Unknown": "All-Rounder",
    "unknown": "All-Rounder",
    "": "All-Rounder",
}


class GeneralHMM:
    """Loads the role-level HMM artifact and predicts form state for a player."""

    def __init__(self, model_path: Path) -> None:
        artifact = joblib.load(model_path)
        self._models: dict = artifact["models"]
        self._state_orders: dict = artifact["state_orders"]
        self._obs_bin_edges: dict = artifact["obs_bin_edges"]

    def _resolve_role(self, role: str) -> str:
        role = str(role or "").strip()
        return _ROLE_ALIASES.get(role, role if role in self._models else "All-Rounder")

    def _discretize(self, points: list[float], edges: np.ndarray) -> list[int]:
        return [int(np.digitize(p, edges) - 1) for p in points]

    def predict(self, role: str, history_points: list[float]) -> dict:
        if len(history_points) < 3:
            return {"state": "unknown", "probs": None, "source": "general"}

        role = self._resolve_role(role)
        model = self._models[role]
        state_order = self._state_orders[role]
        edges = self._obs_bin_edges[role]

        obs = self._discretize(history_points, edges)
        obs_arr = np.array(obs).reshape(-1, 1)

        log_prob, state_seq = model.decode(obs_arr, algorithm="viterbi")
        current_state_idx = state_seq[-1]
        trans_row = model.transmat_[current_state_idx]
        state_name = state_order[current_state_idx]

        named_probs = {state_order[i]: float(trans_row[i]) for i in range(len(trans_row))}
        probs = [
            named_probs.get("cold", 0.0),
            named_probs.get("avg", 0.0),
            named_probs.get("hot", 0.0),
        ]

        return {"state": state_name, "probs": probs, "source": "general"}
