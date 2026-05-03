"""
ELO engine for DraftGenius fantasy cricket.

Design principles
-----------------
* High K-factor by default — T20 form changes fast, Elo must keep up.
* Adaptive K (optional): K decays with experience but resets toward a
  higher value after a long layoff, reflecting "rediscovery" uncertainty.
* Static K override: pass static_k to lock K at a fixed value for all
  updates (useful for testing / deliberately biasing results).
* Inactivity decay: players who go dark for > grace_months months lose
  Elo at a configurable monthly rate, floored at min_rating.
* Multiplier formula: clean z-score conversion, clamped to [0.75, 1.40],
  so the signal is bounded and well-behaved for the GA fitness function.
* Multi-league: processes all leagues in chronological order by match date.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd
from tqdm import tqdm


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FULL_MEMBERS = frozenset(
    {
        "afghanistan", "australia", "bangladesh", "england", "india",
        "ireland", "new zealand", "pakistan", "south africa",
        "sri lanka", "west indies", "zimbabwe",
    }
)
_ALIASES: dict[str, str] = {"wi": "west indies"}


def _norm_team(team: str) -> str:
    return " ".join(str(team).strip().lower().split())


def _is_full_member(team: str) -> bool:
    t = _ALIASES.get(_norm_team(team), _norm_team(team))
    return t in _FULL_MEMBERS


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class EloEngine:
    """
    Parameters
    ----------
    initial_elo : float
        Starting Elo for every new player (default 1500).
    base_k : float
        K-factor applied to established players in franchise / full-member
        international matches (default 64).  Higher than standard chess (32)
        because T20 is noisier and we want fast convergence.
    static_k : float | None
        If set, ALL updates use exactly this K, ignoring adaptive logic.
        Pass a large value (e.g. 120) to "rig" the system for testing.
    adaptive_k : bool
        If True (and static_k is None), K starts high for new players and
        decays toward base_k as they accumulate matches.  Players returning
        after a layoff get a temporary K boost (re-entry uncertainty).
    associate_damping : float
        Fraction of base_k used when both sides are associate nations
        (default 0.15 — their results carry less signal).
    fantasy_scale : float
        Sigmoid scale parameter converting fantasy-points delta to [0, 1]
        actual score.  Higher = gentler curve.  Default 40.
    decay_monthly : float
        Elo points lost per month of inactivity beyond grace_months (default 2.5).
    decay_grace_months : float
        Months without a match before decay starts (default 4).
    decay_floor : float
        Minimum Elo after decay (default 1100).
    """

    def __init__(
        self,
        initial_elo: float = 1500.0,
        base_k: float = 64.0,
        static_k: float | None = None,
        adaptive_k: bool = True,
        associate_damping: float = 0.15,
        fantasy_scale: float = 40.0,
        decay_monthly: float = 2.5,
        decay_grace_months: float = 4.0,
        decay_floor: float = 1100.0,
    ) -> None:
        self.initial_elo = float(initial_elo)
        self.base_k = float(base_k)
        self.static_k = float(static_k) if static_k is not None else None
        self.adaptive_k = adaptive_k
        self.associate_damping = float(min(1.0, max(0.05, associate_damping)))
        self.fantasy_scale = float(max(1.0, fantasy_scale))
        self.decay_monthly = float(decay_monthly)
        self.decay_grace_months = float(decay_grace_months)
        self.decay_floor = float(decay_floor)

    # ------------------------------------------------------------------
    # K-factor logic
    # ------------------------------------------------------------------

    def _match_base_k(self, is_international: bool, teams: list[str]) -> float:
        if self.static_k is not None:
            return self.static_k
        if is_international and not any(_is_full_member(t) for t in teams):
            return self.base_k * self.associate_damping
        return self.base_k

    def _player_k(
        self,
        player_id: str,
        match_base_k: float,
        games_played: dict[str, int],
        last_played: dict[str, pd.Timestamp],
        current_date: pd.Timestamp,
    ) -> float:
        if self.static_k is not None:
            return self.static_k
        if not self.adaptive_k:
            return match_base_k

        gp = games_played.get(player_id, 0)
        if gp < 10:
            exp_multiplier = 2.0
        elif gp >= 30:
            exp_multiplier = 0.75
        else:
            t = (gp - 10) / 20.0
            exp_multiplier = 2.0 - 1.25 * t

        re_entry_boost = 0.0
        lp = last_played.get(player_id)
        if lp is not None and not pd.isna(current_date) and not pd.isna(lp):
            months_away = (current_date - lp).days / 30.0
            if months_away > 6:
                re_entry_boost = 0.5

        return match_base_k * (exp_multiplier + re_entry_boost)

    # ------------------------------------------------------------------
    # Actual score
    # ------------------------------------------------------------------

    def _actual_score(self, player_pts: float, match_avg_pts: float) -> float:
        diff = player_pts - match_avg_pts
        return 1.0 / (1.0 + math.exp(-diff / self.fantasy_scale))

    # ------------------------------------------------------------------
    # Inactivity decay
    # ------------------------------------------------------------------

    def _apply_decay(
        self,
        rating: float,
        last_played: pd.Timestamp | None,
        current_date: pd.Timestamp,
    ) -> float:
        if last_played is None or pd.isna(last_played) or pd.isna(current_date):
            return rating
        months_away = max(0.0, (current_date - last_played).days / 30.0)
        if months_away < self.decay_grace_months:
            return rating
        decay = (months_away - self.decay_grace_months) * self.decay_monthly
        return max(self.decay_floor, rating - decay)

    # ------------------------------------------------------------------
    # Multiplier: Elo → GA fitness weight
    # ------------------------------------------------------------------

    @staticmethod
    def elo_to_multiplier(
        elo: float,
        mean_elo: float,
        std_elo: float,
        lo: float = 0.75,
        hi: float = 1.40,
    ) -> float:
        if std_elo < 1e-6:
            return 1.0
        z = (elo - mean_elo) / (2.0 * std_elo)
        return float(min(hi, max(lo, 1.0 + z)))

    # ------------------------------------------------------------------
    # Core apply()
    # ------------------------------------------------------------------

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        work = df.copy()
        work["_date"] = pd.to_datetime(work["match_date"], errors="coerce")
        work = work.sort_values(["_date", "match_id"]).reset_index(drop=True)

        ratings: dict[str, float] = {}
        games_played: dict[str, int] = {}
        last_played_date: dict[str, pd.Timestamp] = {}
        updates: list[dict[str, Any]] = []

        for match_id, match_group in tqdm(
            work.groupby("match_id", sort=False),
            desc="Computing ELO",
            unit="match",
        ):
            mg = match_group.copy()
            teams = mg["team"].dropna().unique().tolist()
            if len(teams) != 2:
                continue

            is_international = bool(mg["is_international"].iloc[0])
            match_date = mg["_date"].iloc[0]
            match_avg_pts = float(mg["fantasy_points"].mean())
            match_base_k = self._match_base_k(is_international, teams)

            for pid in mg["player_id"].unique():
                if pid in ratings:
                    ratings[pid] = self._apply_decay(
                        ratings[pid], last_played_date.get(pid), match_date
                    )

            player_ids = mg["player_id"].tolist()
            match_avg_elo = sum(
                ratings.get(pid, self.initial_elo) for pid in player_ids
            ) / len(player_ids)

            row_buffer: dict[str, dict[str, Any]] = {}
            deltas: dict[str, float] = {}

            for _, row in mg.iterrows():
                pid = str(row["player_id"])
                pre = ratings.get(pid, self.initial_elo)
                expected = 1.0 / (1.0 + 10.0 ** ((match_avg_elo - pre) / 400.0))
                actual = self._actual_score(float(row["fantasy_points"]), match_avg_pts)
                k_used = self._player_k(
                    pid, match_base_k, games_played, last_played_date, match_date
                )
                delta = k_used * (actual - expected)
                deltas[pid] = deltas.get(pid, 0.0) + delta
                row_buffer[pid] = {
                    "row_index": row.name,
                    "player_elo_pre": pre,
                    "opponent_team_avg_elo": match_avg_elo,
                    "expected_score": expected,
                    "actual_score": actual,
                    "elo_change": delta,
                    "k_factor_used": k_used,
                }

            for pid, delta in deltas.items():
                pre = row_buffer[pid]["player_elo_pre"]
                post = pre + delta
                ratings[pid] = post
                r = row_buffer[pid]
                updates.append({
                    "row_index": r["row_index"],
                    "player_elo_pre": r["player_elo_pre"],
                    "opponent_team_avg_elo": r["opponent_team_avg_elo"],
                    "expected_score": r["expected_score"],
                    "actual_score": r["actual_score"],
                    "elo_change": r["elo_change"],
                    "player_elo_post": post,
                    "k_factor_used": r["k_factor_used"],
                })
                games_played[pid] = games_played.get(pid, 0) + 1
                if not pd.isna(match_date):
                    last_played_date[pid] = match_date

        updates_df = pd.DataFrame(updates).set_index("row_index")
        work = work.join(updates_df, how="left")
        work["fantasy_scale_used"] = self.fantasy_scale

        today = pd.Timestamp.today().normalize()
        work["end_decay_applied"] = 0.0
        for pid, current_rating in list(ratings.items()):
            decayed = self._apply_decay(current_rating, last_played_date.get(pid), today)
            decay_delta = decayed - current_rating
            if abs(decay_delta) < 1e-9:
                continue
            ratings[pid] = decayed
            player_rows = work.index[work["player_id"] == pid]
            if len(player_rows) == 0:
                continue
            last_idx = int(player_rows.max())
            work.at[last_idx, "player_elo_post"] = decayed
            work.at[last_idx, "elo_change"] = float(work.at[last_idx, "elo_change"]) + decay_delta
            work.at[last_idx, "end_decay_applied"] = decay_delta

        all_elo_post = work["player_elo_post"].dropna()
        mean_elo = float(all_elo_post.mean()) if len(all_elo_post) > 0 else 1500.0
        std_elo = float(all_elo_post.std()) if len(all_elo_post) > 1 else 1.0
        work["elo_multiplier"] = work["player_elo_post"].apply(
            lambda e: self.elo_to_multiplier(e, mean_elo, std_elo) if pd.notna(e) else 1.0
        )

        work = work.drop(columns=["_date"])
        work = work.sort_values(["match_date", "match_id", "team", "player_name"]).reset_index(drop=True)
        return work
