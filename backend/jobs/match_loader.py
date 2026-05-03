from __future__ import annotations

from pathlib import Path


class MatchFileLoader:
    def __init__(self, root_dir: Path, league_dirs: dict[str, str]) -> None:
        self.root_dir = root_dir
        self.league_dirs = league_dirs

    def iter_match_files(self) -> list[tuple[str, Path]]:
        files: list[tuple[str, Path]] = []
        for league, rel_dir in self.league_dirs.items():
            league_path = self.root_dir / rel_dir
            if not league_path.exists():
                continue
            for file_path in sorted(league_path.glob("*.json")):
                files.append((league, file_path))
        return files
