"""Credit engine — auto-derives fantasy credits from rolling avg + ELO multiplier."""

from __future__ import annotations

import numpy as np


_CREDIT_STEPS = [6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 10.5]
_PERCENTILE_THRESHOLDS = [10, 20, 30, 45, 60, 72, 83, 92]  # 8 thresholds → 9 buckets


class CreditEngine:
    """Compute credits for a pool of players.

    Uses rolling_avg as the primary signal (falls back to career_avg).
    ELO multiplier bumps/drops the credit by ±0.5.
    Manual overrides (credits_override.json) always win.
    """

    def __init__(self, overrides: dict[str, float] | None = None) -> None:
        self._overrides: dict[str, float] = overrides or {}

    def compute(
        self,
        player_id: str,
        rolling_avg: float | None,
        career_avg: float | None,
        elo_multiplier: float,
        all_avgs: list[float],
    ) -> float:
        """Return credit value (6.5–10.5, step 0.5).

        Parameters
        ----------
        player_id: used to check overrides
        rolling_avg: preferred base; falls back to career_avg
        career_avg: fallback if rolling_avg is unavailable
        elo_multiplier: clamped [0.8, 1.3]
        all_avgs: pool of all players' base averages — used for percentile ranking
        """
        if player_id in self._overrides:
            return float(self._overrides[player_id])

        base = rolling_avg if rolling_avg is not None else career_avg
        if base is None or len(all_avgs) == 0:
            return 8.0  # neutral default

        percentile = float(np.mean([a <= base for a in all_avgs])) * 100
        bucket = np.searchsorted(_PERCENTILE_THRESHOLDS, percentile, side="right")
        credit = _CREDIT_STEPS[int(bucket)]

        # ELO adjustment
        if elo_multiplier > 1.1:
            credit = min(credit + 0.5, 10.5)
        elif elo_multiplier < 0.9:
            credit = max(credit - 0.5, 6.5)

        return float(credit)
