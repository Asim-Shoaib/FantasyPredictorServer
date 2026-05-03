from __future__ import annotations

import json
from pathlib import Path

from backend.utils.models import PlayerData


class MatchParser:
    def parse_match(self, league: str, file_path: Path) -> dict[str, PlayerData]:
        with file_path.open("r", encoding="utf-8") as f:
            match_json = json.load(f)

        info = match_json.get("info", {})
        players_by_team = info.get("players", {})
        registry_people = info.get("registry", {}).get("people", {})
        teams = list(players_by_team.keys())

        match_date = str(info.get("dates", [""])[0]) if info.get("dates") else ""
        match_id = file_path.stem
        event_name = str(info.get("event", {}).get("name", ""))
        team_type = str(info.get("team_type", ""))
        is_international = team_type.lower() == "international"

        playing_names: set[str] = set()
        name_to_team: dict[str, str] = {}
        for team_name, team_players in players_by_team.items():
            for player_name in team_players:
                playing_names.add(player_name)
                name_to_team[player_name] = team_name

        name_to_id: dict[str, str] = {}
        for player_name in playing_names:
            player_id = registry_people.get(player_name)
            if player_id:
                name_to_id[player_name] = player_id

        player_data: dict[str, PlayerData] = {}
        for player_name, player_id in name_to_id.items():
            # Always capture team name — applies to both franchise and international matches.
            # Previously franchise matches forced this to "" which made the raw CSV unusable
            # for opposition-based analysis and confused debugging.
            team_name = name_to_team.get(player_name, "")
            opposition = ""
            if len(teams) == 2 and team_name:
                opposition = teams[1] if team_name == teams[0] else teams[0]

            player_data[player_id] = PlayerData(
                player_id=player_id,
                player_name=player_name,
                team=team_name,
                league=league,
                opposition=opposition,
                match_id=match_id,
                venue=info.get("venue", ""),
                match_date=match_date,
                event_name=event_name,
                team_type=team_type,
                is_international=is_international,
            )

        dismissed_player_ids: set[str] = set()
        over_tracker: dict[str, dict[int, dict[str, int]]] = {}

        for innings in match_json.get("innings", []):
            for over_data in innings.get("overs", []):
                over_number = over_data.get("over")
                for delivery in over_data.get("deliveries", []):
                    batter_id = name_to_id.get(delivery.get("batter"))
                    bowler_id = name_to_id.get(delivery.get("bowler"))
                    runs = delivery.get("runs", {})
                    extras = delivery.get("extras", {})

                    batter_runs = int(runs.get("batter", 0))
                    total_runs = int(runs.get("total", 0))
                    wides = int(extras.get("wides", 0))
                    noballs = int(extras.get("noballs", 0))

                    if batter_id in player_data:
                        pdata = player_data[batter_id]
                        pdata.did_bat = True
                        pdata.runs_scored += batter_runs
                        if wides == 0:
                            pdata.balls_faced += 1
                        if batter_runs == 4:
                            pdata.fours += 1
                        elif batter_runs == 6:
                            pdata.sixes += 1

                    if bowler_id in player_data:
                        bdata = player_data[bowler_id]
                        conceded_this_ball = batter_runs + wides + noballs
                        bdata.runs_conceded += conceded_this_ball

                        legal_delivery = wides == 0 and noballs == 0
                        if legal_delivery and total_runs == 0:
                            bdata.dot_balls += 1

                        if over_number is not None:
                            over_info = over_tracker.setdefault(bowler_id, {}).setdefault(
                                over_number,
                                {"legal": 0, "conceded": 0},
                            )
                            if legal_delivery:
                                over_info["legal"] += 1
                            over_info["conceded"] += conceded_this_ball

                    for wicket in delivery.get("wickets", []):
                        kind = wicket.get("kind", "")
                        out_id = name_to_id.get(wicket.get("player_out"))
                        fielders = wicket.get("fielders", [])

                        if out_id in player_data:
                            dismissed_player_ids.add(out_id)

                        if bowler_id in player_data and kind not in {
                            "run out",
                            "retired hurt",
                            "retired out",
                            "obstructing the field",
                        }:
                            player_data[bowler_id].wickets += 1
                            if kind == "lbw":
                                player_data[bowler_id].lbw_wickets += 1
                            if kind in {"bowled", "caught and bowled"}:
                                player_data[bowler_id].bowled_wickets += 1

                        if kind == "caught and bowled":
                            if bowler_id in player_data:
                                player_data[bowler_id].catches += 1
                        elif kind == "caught":
                            for fielder in fielders:
                                fielder_name = fielder.get("name") if isinstance(fielder, dict) else fielder
                                fielder_id = name_to_id.get(fielder_name)
                                if fielder_id in player_data:
                                    player_data[fielder_id].catches += 1

                        if kind == "stumped" and fielders:
                            stumper = fielders[0]
                            stumper_name = stumper.get("name") if isinstance(stumper, dict) else stumper
                            stumper_id = name_to_id.get(stumper_name)
                            if stumper_id in player_data:
                                player_data[stumper_id].stumpings += 1

                        if kind == "run out" and fielders:
                            direct = False
                            if len(fielders) == 1:
                                fielder = fielders[0]
                                if isinstance(fielder, dict):
                                    direct = bool(fielder.get("direct", True))
                                else:
                                    direct = True

                            for fielder in fielders:
                                fielder_name = fielder.get("name") if isinstance(fielder, dict) else fielder
                                fielder_id = name_to_id.get(fielder_name)
                                if fielder_id not in player_data:
                                    continue
                                if direct:
                                    player_data[fielder_id].direct_runouts += 1
                                else:
                                    player_data[fielder_id].indirect_runouts += 1

        for bowler_id, bowler_data in player_data.items():
            legal_balls = 0
            maiden_overs = 0
            for over_info in over_tracker.get(bowler_id, {}).values():
                legal_balls += over_info["legal"]
                if over_info["legal"] == 6 and over_info["conceded"] == 0:
                    maiden_overs += 1
            bowler_data.overs_bowled = legal_balls / 6
            bowler_data.maiden_overs = maiden_overs

        for player_id, pdata in player_data.items():
            pdata.dismissed_for_duck = (
                pdata.did_bat and pdata.runs_scored == 0 and player_id in dismissed_player_ids
            )

        return player_data
