from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from path_bootstrap import pythonpath_env


ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str]) -> None:
    subprocess.run(args, cwd=ROOT, check=True, env=pythonpath_env())


def main() -> None:
    run([sys.executable, "-m", "pytest", "-c", str(ROOT / "pytest.ini"), str(ROOT / "tests")])
    run([sys.executable, str(ROOT / "workers" / "briefs" / "smoke.py")])
    print("L3 PIPELINE: PASS")


if __name__ == "__main__":
    main()
