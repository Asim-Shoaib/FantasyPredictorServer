from __future__ import annotations

import pandas as pd


class FantasyPointsCalculator:
    @staticmethod
    def batting_milestone_bonus(runs: int) -> int:
        if runs >= 100:
            return 16
        if runs >= 75:
            return 12
        if runs >= 50:
            return 8
        if runs >= 25:
            return 4
        return 0

    @staticmethod
    def wicket_haul_bonus(wickets: int) -> int:
        if wickets >= 5:
            return 12
        if wickets >= 4:
            return 8
        if wickets >= 3:
            return 4
        return 0

    @staticmethod
    def economy_rate_points(overs_bowled: float, runs_conceded: int) -> int:
        if overs_bowled < 2:
            return 0
        economy = runs_conceded / overs_bowled if overs_bowled else 0
        if economy < 5:
            return 6
        if 5 <= economy < 6:
            return 4
        if 6 <= economy <= 7:
            return 2
        if 10 <= economy <= 11:
            return -2
        if 11 < economy <= 12:
            return -4
        if economy > 12:
            return -6
        return 0

    @staticmethod
    def normalize_role(player_role: str) -> str:
        return str(player_role or "").strip().lower()

    def strike_rate_points(self, player_role: str, balls_faced: int, runs_scored: int) -> int:
        role = self.normalize_role(player_role)
        is_designated_bowler = "bowler" in role and "all" not in role
        if is_designated_bowler or balls_faced < 10:
            return 0

        strike_rate = (runs_scored / balls_faced) * 100 if balls_faced else 0
        if strike_rate > 170:
            return 6
        if 150 < strike_rate <= 170:
            return 4
        if 130 <= strike_rate <= 150:
            return 2
        if 60 <= strike_rate <= 70:
            return -2
        if 50 <= strike_rate < 60:
            return -4
        if strike_rate < 50:
            return -6
        return 0

    def compute_row(self, row: pd.Series) -> pd.Series:
        batting_points = 0
        batting_points += int(row["runs_scored"]) * 1
        batting_points += int(row["fours"]) * 4
        batting_points += int(row["sixes"]) * 6
        batting_points += self.batting_milestone_bonus(int(row["runs_scored"]))

        bowling_points = 0
        bowling_points += int(row["wickets"]) * 30
        bowling_points += (int(row["lbw_wickets"]) + int(row["bowled_wickets"])) * 8
        bowling_points += self.wicket_haul_bonus(int(row["wickets"]))
        bowling_points += int(row["maiden_overs"]) * 12
        bowling_points += int(row["dot_balls"]) * 1

        fielding_points = 0
        fielding_points += int(row["catches"]) * 8
        if int(row["catches"]) >= 3:
            fielding_points += 4
        fielding_points += int(row["stumpings"]) * 12
        fielding_points += int(row["direct_runouts"]) * 12
        fielding_points += int(row["indirect_runouts"]) * 6

        eco_points = self.economy_rate_points(float(row["overs_bowled"]), int(row["runs_conceded"]))
        sr_points = self.strike_rate_points(
            row.get("player_role", ""),
            int(row["balls_faced"]),
            int(row["runs_scored"]),
        )

        total_points = batting_points + bowling_points + fielding_points + eco_points + sr_points
        return pd.Series({
            "batting_points": batting_points,
            "bowling_points": bowling_points,
            "fielding_points": fielding_points,
            "economy_rate_points": eco_points,
            "strike_rate_points": sr_points,
            "fantasy_points": total_points,
        })
