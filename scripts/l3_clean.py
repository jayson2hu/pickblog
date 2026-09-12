from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PATHS = [
    ROOT / ".pytest_cache",
    ROOT / "services" / "shared" / "codepick_l3.egg-info",
    ROOT / "apps" / "reader-web" / "tsconfig.tsbuildinfo",
    ROOT / "apps" / "reader-web" / "test-results",
    ROOT / "apps" / "reader-web" / "playwright-report",
    ROOT / "apps" / "reader-web" / ".next",
]

skipped: list[str] = []


def remove_path(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        return True
    except OSError as exc:
        skipped.append(f"{path.relative_to(ROOT).as_posix()} ({exc})")
        return False


def main() -> None:
    removed = [path.relative_to(ROOT).as_posix() for path in PATHS if remove_path(path)]
    for pycache in ROOT.rglob("__pycache__"):
        if pycache.is_dir():
            shutil.rmtree(pycache)
            removed.append(pycache.relative_to(ROOT).as_posix())
    if removed:
        print("Removed L3 generated artifacts:")
        for path in sorted(removed):
            print(f"- {path}")
    else:
        print("No L3 generated artifacts found.")
    if skipped:
        print("Skipped locked artifacts:")
        for path in sorted(skipped):
            print(f"- {path}")


if __name__ == "__main__":
    main()
