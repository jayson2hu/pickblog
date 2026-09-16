import os
import uvicorn

from path_bootstrap import ensure_paths


def main() -> None:
    ensure_paths()
    uvicorn.run(
        "public_api.main:app",
        host=os.getenv("PUBLIC_API_HOST", "127.0.0.1"),
        port=int(os.getenv("PUBLIC_API_PORT", "8001")),
        reload=os.getenv("PUBLIC_API_RELOAD", "false").lower() == "true",
    )


if __name__ == "__main__":
    main()
