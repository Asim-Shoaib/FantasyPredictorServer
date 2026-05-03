from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path


CRICSHEET_BASE_URL = "https://cricsheet.org/downloads"

LEAGUE_ARCHIVE_NAMES: dict[str, str] = {
    "bbl": "bbl_male_json",
    "ipl": "ipl_male_json",
    "psl": "psl_male_json",
    "bpl": "bpl_male_json",
    "cpl": "cpl_male_json",
    "sa20": "sa20_male_json",
    "ilt20": "ilt20_male_json",
    "lpl": "lpl_male_json",
    "t20s": "t20s_male_json",
}


@dataclass
class UpdateResult:
    new_files: dict[str, list[Path]] = field(default_factory=dict)
    skipped: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class CricsheetUpdater:
    def __init__(
        self,
        root_dir: Path,
        league_dirs: dict[str, str],
        download_cache_dir: Path,
    ) -> None:
        self.root_dir = root_dir
        self.league_dirs = league_dirs
        self.download_cache_dir = download_cache_dir
        self.download_cache_dir.mkdir(parents=True, exist_ok=True)

    def _etags_path(self) -> Path:
        return self.download_cache_dir / "etags.json"

    def _load_etags(self) -> dict[str, str]:
        p = self._etags_path()
        if not p.exists():
            return {}
        try:
            with p.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_etags(self, etags: dict[str, str]) -> None:
        with self._etags_path().open("w", encoding="utf-8") as f:
            json.dump(etags, f, indent=2)

    def _download_zip(self, league: str, url: str) -> tuple[Path | None, bool]:
        etags = self._load_etags()
        dest = self.download_cache_dir / f"{league}_male_json.zip"

        req = urllib.request.Request(url)
        if league in etags and dest.exists():
            req.add_header("If-None-Match", etags[league])

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                new_etag = resp.headers.get("ETag", "")
                data = resp.read()
                tmp_fd, tmp_name = tempfile.mkstemp(dir=self.download_cache_dir)
                try:
                    with os.fdopen(tmp_fd, "wb") as f:
                        f.write(data)
                    Path(tmp_name).replace(dest)
                except Exception:
                    os.unlink(tmp_name)
                    raise
                if new_etag:
                    etags[league] = new_etag
                    self._save_etags(etags)
                return dest, True
        except urllib.error.HTTPError as exc:
            if exc.code == 304:
                return dest if dest.exists() else None, False
            raise

    def _extract_new_files(self, zip_path: Path, dest_dir: Path) -> tuple[list[Path], int]:
        dest_dir.mkdir(parents=True, exist_ok=True)
        new_files: list[Path] = []
        skipped = 0
        seen_names: set[str] = set()

        with tempfile.TemporaryDirectory() as tmp_dir:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmp_dir)

            for extracted in sorted(Path(tmp_dir).rglob("*.json")):
                name = extracted.name
                target = dest_dir / name

                if name in seen_names:
                    print(
                        f"WARNING: _extract_new_files: duplicate basename '{name}' in zip; skipping.",
                        file=sys.stderr,
                    )
                    skipped += 1
                    continue

                seen_names.add(name)

                if target.exists():
                    skipped += 1
                    continue

                shutil.copy2(extracted, target)
                new_files.append(target)

        return new_files, skipped

    def update_all(self) -> UpdateResult:
        result = UpdateResult()
        league_urls: dict[str, str] = getattr(self, "_league_urls", None) or {
            league: f"{CRICSHEET_BASE_URL}/{LEAGUE_ARCHIVE_NAMES[league]}.zip"
            for league in self.league_dirs
            if league in LEAGUE_ARCHIVE_NAMES
        }

        for league, url in league_urls.items():
            rel_dir = self.league_dirs.get(league, f"data/{league}_male_json")
            dest_dir = self.root_dir / rel_dir

            try:
                zip_path, was_downloaded = self._download_zip(league, url)
            except Exception as exc:
                result.errors.append(f"[{league}] download failed: {exc}")
                continue

            if not was_downloaded:
                result.skipped[league] = result.skipped.get(league, 0)
                continue

            if zip_path is None:
                result.errors.append(f"[{league}] zip path unavailable after download")
                continue

            try:
                new_files, skipped_count = self._extract_new_files(zip_path, dest_dir)
            except Exception as exc:
                result.errors.append(f"[{league}] extraction failed: {exc}")
                continue

            result.skipped[league] = skipped_count
            validated: list[Path] = []
            for fpath in new_files:
                if self._validate_json(fpath):
                    validated.append(fpath)
                else:
                    result.errors.append(f"[{league}] invalid JSON removed: {fpath.name}")
                    fpath.unlink(missing_ok=True)

            if validated:
                result.new_files[league] = validated

        return result

    def _validate_json(self, file_path: Path) -> bool:
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            info = data.get("info", {})
            return (
                "innings" in data
                and isinstance(info.get("dates"), list)
                and len(info["dates"]) > 0
            )
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            return False
