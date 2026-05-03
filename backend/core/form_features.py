from __future__ import annotations

import pandas as pd


class FormFeatureBuilder:
    """Adds rolling window fantasy points average per player.

    Uses strictly prior matches only (no lookahead) — the current match's
    own fantasy_points are excluded from its own rolling average via shift(1).
    """

    def __init__(self, window: int = 10, min_matches: int = 3) -> None:
        self.window = window
        self.min_matches = min_matches

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in ("rolling_avg_pts", "rolling_matches"):
            if col in df.columns:
                df = df.drop(columns=[col])

        result = df.copy()
        result["match_date"] = pd.to_datetime(result["match_date"], errors="coerce")
        result = result.sort_values(["match_date", "match_id"]).reset_index(drop=True)

        rolled = (
            result.groupby("player_id")["fantasy_points"]
            .transform(
                lambda s: s.shift(1)
                .rolling(window=self.window, min_periods=self.min_matches)
                .mean()
            )
        )
        counts = (
            result.groupby("player_id")["fantasy_points"]
            .transform(
                lambda s: s.shift(1)
                .rolling(window=self.window, min_periods=self.min_matches)
                .count()
            )
        )

        result["rolling_avg_pts"] = rolled
        result["rolling_matches"] = counts.where(rolled.notna()).astype("Int64")
        return result
