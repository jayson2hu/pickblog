import uvicorn

from path_bootstrap import ensure_paths


if __name__ == "__main__":
    ensure_paths()
    uvicorn.run("reader_api.main:app", host="127.0.0.1", port=8000, reload=True)
