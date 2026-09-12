from __future__ import annotations

from path_bootstrap import ensure_paths


if __name__ == "__main__":
    ensure_paths()
    from server import smoke
    import json

    print(json.dumps(smoke(), indent=2, sort_keys=True))
