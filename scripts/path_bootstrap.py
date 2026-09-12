from __future__ import annotations

import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
PYTHONPATHS = [
    ROOT / "services" / "shared",
    ROOT / "services" / "reader-api",
    ROOT / "services" / "public-api",
    ROOT / "workers" / "briefs",
    ROOT / "services" / "mcp-server",
]


def ensure_paths() -> None:
    for path in reversed(PYTHONPATHS):
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)


def pythonpath_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    paths = [str(path) for path in PYTHONPATHS]
    if existing:
        paths.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env
