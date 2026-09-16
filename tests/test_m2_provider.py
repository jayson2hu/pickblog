from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
from fastapi.testclient import TestClient

from codepick_l3.provider import L2HttpContentReadProvider, ProviderUnavailable
from reader_api.main import app


def test_l2_http_provider_maps_404_to_missing_content() -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(404)
            self.end_headers()

        def log_message(self, format: str, *args) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        provider = L2HttpContentReadProvider(
            f"http://127.0.0.1:{server.server_port}", timeout=2
        )
        with pytest.raises(KeyError):
            provider.get("missing/content")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_reader_api_maps_l2_outage_to_retryable_503(monkeypatch) -> None:
    class BrokenProvider:
        def list(self, *args, **kwargs):
            raise ProviderUnavailable("L2 is offline")

    monkeypatch.setattr(
        "reader_api.routers.feed.get_content_provider", lambda: BrokenProvider()
    )
    response = TestClient(app).get("/api/feed")
    assert response.status_code == 503
    assert response.headers["retry-after"] == "2"
    assert response.json()["detail"] == {
        "code": "l2_unavailable",
        "message": "L2 is offline",
        "retryable": True,
    }
