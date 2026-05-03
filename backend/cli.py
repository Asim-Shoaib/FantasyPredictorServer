from __future__ import annotations

import argparse
import logging
from pathlib import Path

from backend.utils.config import PipelineConfig
from backend.jobs.pipeline import Pipeline

logger = logging.getLogger(__name__)


MAJOR_T20_LEAGUE_DIRS: dict[str, str] = {
    "psl": "data/psl_male_json",
    "ipl": "data/ipl_male_json",
    "bbl": "data/bbl_male_json",
    "bpl": "data/bpl_male_json",
    "cpl": "data/cpl_male_json",
    "sa20": "data/sa20_male_json",
    "ilt20": "data/ilt20_male_json",
    "lpl": "data/lpl_male_json",
}


def _parse_league_keys(raw: str) -> list[str]:
    keys: list[str] = []
    for part in raw.split(","):
        key = part.strip().lower()
        if key and key not in keys:
            keys.append(key)

    if not keys:
        raise ValueError("--leagues must include at least one league key.")

    unknown = sorted(set(keys) - set(MAJOR_T20_LEAGUE_DIRS))
    if unknown:
        known = ", ".join(sorted(MAJOR_T20_LEAGUE_DIRS))
        raise ValueError(
            f"Unknown league keys: {', '.join(unknown)}. Supported keys: {known}"
        )
    return keys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build fantasy points dataset from Cricsheet-style JSONs."
    )
    parser.add_argument("--root-dir", default=".", help="Workspace root directory.")
    parser.add_argument(
        "--people-csv",
        default="data/people.csv",
        help="Path to people.csv.",
    )
    parser.add_argument(
        "--output-csv",
        default="data/output/all_leagues_player_match.csv",
        help="Output CSV file path.",
    )
    parser.add_argument(
        "--update-data",
        action="store_true",
        default=False,
        help="Download new match data from Cricsheet before running.",
    )
    parser.add_argument(
        "--cutoff-years",
        type=int,
        default=5,
        help="Only include matches from the last N years. 0 = no cutoff (default: 5).",
    )
    parser.add_argument(
        "--leagues",
        default=",".join(MAJOR_T20_LEAGUE_DIRS.keys()),
        help=(
            "Comma-separated league keys to ingest. "
            "Default includes major T20 leagues (PSL, IPL, BBL, BPL, CPL, SA20, ILT20, LPL)."
        ),
    )
    parser.add_argument(
        "--force-pipeline",
        action="store_true",
        default=False,
        help=(
            "Re-run the full scoring + EloEngine pipeline on ALL existing match files, "
            "even if no new data was downloaded. Useful when scoring rules or Elo "
            "parameters change and the CSV needs to be regenerated from scratch."
        ),
    )
    parser.add_argument(
        "--fetch-photos",
        action="store_true",
        default=False,
        help="Fetch ESPN headshots for all players in the roster after the pipeline completes.",
    )
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> PipelineConfig:
    root = Path(args.root_dir).resolve()
    league_keys = _parse_league_keys(str(args.leagues))
    league_dirs = {k: MAJOR_T20_LEAGUE_DIRS[k] for k in league_keys}

    output_dir = root / "data" / "output"
    return PipelineConfig(
        root_dir=root,
        league_dirs=league_dirs,
        people_csv=(root / args.people_csv).resolve(),
        output_csv=(root / args.output_csv).resolve(),
        role_cache_json=(output_dir / "role_cache.json").resolve(),
        final_results_cache_parquet=(root / ".cache" / "final_results_cache.parquet").resolve(),
        cutoff_years=int(args.cutoff_years),
    )


def main() -> None:
    args = parse_args()
    root = Path(args.root_dir).resolve()

    config = build_config(args)
    config.output_csv.parent.mkdir(parents=True, exist_ok=True)
    config.role_cache_json.parent.mkdir(parents=True, exist_ok=True)

    if args.update_data:
        from backend.jobs.data_updater import CricsheetUpdater

        updater = CricsheetUpdater(
            root_dir=config.root_dir,
            league_dirs=config.league_dirs,
            download_cache_dir=config.root_dir / ".cache" / "downloads",
        )
        update_result = updater.update_all()
        total_new = sum(len(v) for v in update_result.new_files.values())
        total_skipped = sum(update_result.skipped.values())
        print(
            f"Data update: {total_new} new files, {total_skipped} unchanged, "
            f"{len(update_result.errors)} errors."
        )
        for err in update_result.errors:
            print(f"  WARNING: {err}")

        if total_new == 0 and not args.force_pipeline:
            print("No new match data. Skipping pipeline. (Use --force-pipeline to override.)")
            return
        if total_new > 0:
            print(f"New data detected ({total_new} files). Running pipeline...")
        else:
            print("No new files, but --force-pipeline was set. Re-running pipeline on all data...")

    pipeline = Pipeline(config)
    result = pipeline.run()

    from backend.core.form_features import FormFeatureBuilder

    required_cols = {"player_id", "match_id", "match_date", "fantasy_points"}
    if required_cols.issubset(result.columns):
        result = FormFeatureBuilder().apply(result)
    else:
        missing = sorted(required_cols - set(result.columns))
        print(f"Skipping form features (missing columns: {', '.join(missing)}).")

    # Write intermediate scored CSV (no Elo columns yet)
    result.to_csv(config.output_csv, index=False)
    print(f"Wrote {len(result)} scored records to {config.output_csv.name}")
    if "rolling_avg_pts" in result.columns:
        print(f"Players with rolling avg: {result['rolling_avg_pts'].notna().sum()}")

    # ── Apply EloEngine and write the file data_cache.py actually reads ──────
    _apply_elo_and_save(result, root)

    # ── Optionally refresh ESPN photos ────────────────────────────────────────
    if args.fetch_photos:
        _fetch_photos_cli(config, root)


def _apply_elo_and_save(scored_df: "pd.DataFrame", root: Path) -> None:
    """Run EloEngine.apply() on the scored DataFrame and save to the canonical
    ELO CSV path that data_cache.py reads at server startup.
    """
    import pandas as pd
    from backend.core.elo_engine import EloEngine

    elo_csv_path = root / "data" / "all_leagues_player_match_elo.csv"

    required = {"player_id", "match_id", "match_date", "fantasy_points", "is_international", "team"}
    missing = required - set(scored_df.columns)
    if missing:
        print(f"WARNING: Cannot run EloEngine — missing columns: {', '.join(sorted(missing))}")
        print("  Elo CSV was NOT updated.")
        return

    print("Running EloEngine across all leagues (this may take a minute)...")
    try:
        elo_df = EloEngine().apply(scored_df)
        elo_csv_path.parent.mkdir(parents=True, exist_ok=True)
        elo_df.to_csv(elo_csv_path, index=False)
        print(
            f"Elo CSV written: {len(elo_df)} rows → {elo_csv_path.relative_to(root)}\n"
            f"  elo_multiplier range: "
            f"[{elo_df['elo_multiplier'].min():.3f}, {elo_df['elo_multiplier'].max():.3f}]"
        )
    except Exception as exc:
        logger.error("EloEngine failed: %s", exc, exc_info=True)
        print(f"ERROR: EloEngine failed — {exc}\n  Elo CSV was NOT updated.")


def _fetch_photos_cli(config: "PipelineConfig", root: Path) -> None:
    """Fetch ESPN headshots after a pipeline run and save to player_profiles.json.

    Uses Cricsheet identifier as the key (same as ELO CSV player_id) so that
    player_service.py can look up photos correctly.
    """
    import pandas as pd
    from backend.services.profile_fetcher import ProfileFetcher

    people_csv = config.people_csv
    output_path = root / "data" / "output" / "player_profiles.json"
    elo_csv = root / "data" / "all_leagues_player_match_elo.csv"

    if not people_csv.exists():
        print(f"WARNING: people.csv not found at {people_csv} — skipping photo fetch.")
        return
    if not elo_csv.exists():
        print("WARNING: ELO CSV not found — skipping photo fetch.")
        return

    try:
        people_df = pd.read_csv(people_csv, dtype=str, low_memory=False).fillna("")
        if "identifier" not in people_df.columns or "key_cricinfo" not in people_df.columns:
            print("WARNING: people.csv missing 'identifier'/'key_cricinfo' columns — skipping photo fetch.")
            return

        # Build identifier → cricinfo_id map
        identifier_to_cricinfo: dict[str, str] = {}
        for _, row in people_df.iterrows():
            ident = str(row["identifier"]).strip()
            cid = str(row["key_cricinfo"]).strip()
            if not ident or not cid or cid in ("", "nan"):
                continue
            if cid.endswith(".0"):
                cid = cid[:-2]
            identifier_to_cricinfo[ident] = cid

        # Build the player_map from ELO CSV unique player_ids
        elo_df = pd.read_csv(elo_csv, usecols=["player_id"], low_memory=False)
        player_map: dict[str, str] = {}
        for pid in elo_df["player_id"].dropna().unique():
            pid_str = str(pid).strip()
            cid = identifier_to_cricinfo.get(pid_str)
            if cid:
                player_map[pid_str] = cid

        print(f"Fetching ESPN photos for {len(player_map)} players...")
        fetcher = ProfileFetcher(people_csv=people_csv, output_path=output_path)
        profiles = fetcher.run(player_ids=player_map)
        with_photo = sum(1 for p in profiles.values() if isinstance(p, dict) and p.get("photo_url"))
        print(f"Photos saved: {with_photo}/{len(player_map)} with headshot URL → {output_path.name}")

    except Exception as exc:
        logger.error("Photo fetch failed: %s", exc, exc_info=True)
        print(f"ERROR: Photo fetch failed — {exc}")


if __name__ == "__main__":
    main()
