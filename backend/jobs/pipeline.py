from __future__ import annotations

import asyncio

import pandas as pd
from tqdm import tqdm

from backend.utils.config import PipelineConfig
from backend.jobs.match_loader import MatchFileLoader
from backend.jobs.match_parser import MatchParser
from backend.utils.smart_cache import SmartMatchCache
from backend.services.role_resolver import PlayerRoleResolver
from backend.core.scoring import FantasyPointsCalculator


class Pipeline:
    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.loader = MatchFileLoader(config.root_dir, config.league_dirs)
        self.parser = MatchParser()
        self.cache = SmartMatchCache(
            final_results_cache_path=config.final_results_cache_parquet,
        )
        self.role_resolver = PlayerRoleResolver(
            people_csv_path=config.people_csv,
            role_cache_path=config.role_cache_json,
            request_delay_seconds=config.request_delay_seconds,
        )
        self.scorer = FantasyPointsCalculator()

    def run(self) -> pd.DataFrame:
        all_records: list[dict] = []
        player_lookup: dict[str, str] = {}
        newly_parsed_count = 0
        cached_count = 0

        match_files = self.loader.iter_match_files()
        for league, path in tqdm(match_files, desc="Parsing matches", unit="match"):
            records, is_new = self.cache.get_or_parse_match(league, path, self.parser)
            if is_new:
                newly_parsed_count += 1
            else:
                cached_count += 1
            all_records.extend(records)
            for row in records:
                player_lookup[row["player_id"]] = row["player_name"]

        cached_records = self.cache.load_all_cached_records(cutoff_date=self.config.cutoff_date)
        all_records.extend(cached_records)
        for row in cached_records:
            player_lookup[row["player_id"]] = row["player_name"]

        self.cache.save_cache()
        print(f"Matches parsed: new={newly_parsed_count}, cached={cached_count}, total={len(all_records)}")

        role_map = asyncio.run(self.role_resolver.resolve_roles_bulk(player_lookup))

        for row in all_records:
            row["player_role"] = role_map.get(row["player_id"], "Unknown")

        self.role_resolver.save_cache()

        records_df = pd.DataFrame(all_records)
        if records_df.empty:
            raise RuntimeError("No records parsed. Check league directories and match JSON format.")

        points_breakdown = records_df.apply(self.scorer.compute_row, axis=1)
        with_points = pd.concat([records_df, points_breakdown], axis=1)

        with_points = self._infer_unknown_roles(with_points)

        with_points["match_date"] = pd.to_datetime(with_points["match_date"], errors="coerce")
        result = with_points.sort_values(
            ["match_date", "match_id", "player_name"]
        ).reset_index(drop=True)

        result.to_csv(self.config.output_csv, index=False)
        return result

    def _infer_unknown_roles(self, df: pd.DataFrame) -> pd.DataFrame:
        unknown = df[df["player_role"] == "Unknown"]["player_id"].unique()
        if len(unknown) == 0:
            return df
        print(f"Inferring roles for {len(unknown)} unknown players...")
        for pid in unknown:
            rows = df[df["player_id"] == pid]
            inferred = self.role_resolver.infer_role_from_stats(
                rows["batting_points"].mean(),
                rows["bowling_points"].mean(),
                rows["fielding_points"].mean(),
            )
            df.loc[df["player_id"] == pid, "player_role"] = inferred
            self.role_resolver.role_cache[pid] = inferred
        self.role_resolver.save_cache()
        return df
