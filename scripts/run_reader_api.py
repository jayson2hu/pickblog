import os

import uvicorn

from path_bootstrap import ensure_paths


if __name__ == "__main__":
    ensure_paths()
    uvicorn.run(
        "reader_api.main:app",
        host=os.getenv("READER_API_HOST", "127.0.0.1"),
        port=int(os.getenv("READER_API_PORT", "8000")),
        reload=os.getenv("READER_API_RELOAD", "false").lower() == "true",
    )
