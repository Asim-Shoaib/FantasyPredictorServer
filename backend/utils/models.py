from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PlayerData:
    player_id: str = ""
    player_name: str = ""
    player_role: str = ""
    team: str = ""
    league: str = ""
    match_id: str = ""
    opposition: str = ""
    venue: str = ""
    match_date: str = ""
    event_name: str = ""
    team_type: str = ""
    is_international: bool = False

    runs_scored: int = 0
    balls_faced: int = 0
    fours: int = 0
    sixes: int = 0
    dismissed_for_duck: bool = False
    did_bat: bool = False

    overs_bowled: float = 0.0
    runs_conceded: int = 0
    wickets: int = 0
    dot_balls: int = 0
    maiden_overs: int = 0
    lbw_wickets: int = 0
    bowled_wickets: int = 0

    catches: int = 0
    stumpings: int = 0
    direct_runouts: int = 0
    indirect_runouts: int = 0
