from __future__ import annotations

import json
from pathlib import Path
import runpy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
import uvicorn

from codepick_l3.provider import (
    L2HttpContentReadProvider,
    ProviderConfigurationError,
    ProviderRequestError,
    ProviderUnavailable,
    StubContentReadProvider,
)
from codepick_l3.usage import quota_store
from public_api.main import app as public_app
import server as mcp_server


public = TestClient(public_app)


def api_headers(raw_key: str) -> dict[str, str]:
    quota_store.add_key(raw_key, daily_quota=50, rpm=50)
    return {"X-API-Key": raw_key}


def search_fixture(tmp_path) -> StubContentReadProvider:
    template = StubContentReadProvider().get("cp-001").model_dump(mode="json")
    rows = []
    for content_id, title, summary, quality, published_at in [
        ("unrelated", "Highest unrelated", "No requested phrase", 99, "2026-09-16T12:00:00Z"),
        ("match-1", "Needle first", "Requested phrase", 90, "2026-09-15T12:00:00Z"),
        ("match-2", "Second result", "Contains needle in summary", 80, "2026-09-14T12:00:00Z"),
    ]:
        item = dict(template)
        item.update(
            id=content_id,
            title=title,
            summary=summary,
            published_at=published_at,
            scores={**item["scores"], "quality": quality},
        )
        rows.append(item)
    path = tmp_path / "search.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    return StubContentReadProvider(path)


def test_stub_search_filters_before_cursor_pagination(tmp_path) -> None:
    provider = search_fixture(tmp_path)
    first = provider.list(limit=1, filters={"q": " needle ", "sort": "score"})
    second = provider.list(
        cursor=first.next_cursor,
        limit=1,
        filters={"q": "needle", "sort": "score"},
    )

    assert [item.id for item in first.items] == ["match-1"]
    assert first.total == 2
    assert first.next_cursor == "1"
    assert [item.id for item in second.items] == ["match-2"]
    assert second.total == 2
    assert second.next_cursor is None


def test_public_and_mcp_search_share_server_side_query_semantics(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = search_fixture(tmp_path)
    monkeypatch.setattr("public_api.routers.v1.get_content_provider", lambda: provider)
    monkeypatch.setattr(mcp_server, "get_content_provider", lambda: provider)
    headers = api_headers("server_search_key")

    first = public.get(
        "/v1/search", params={"q": "needle", "limit": 1}, headers=headers
    )
    second = public.get(
        "/v1/search",
        params={"q": "needle", "limit": 1, "cursor": first.json()["next_cursor"]},
        headers=headers,
    )
    mcp = mcp_server.search("needle", limit=2)

    assert first.status_code == 200
    assert [item["id"] for item in first.json()["items"]] == ["match-1"]
    assert [item["id"] for item in second.json()["items"]] == ["match-2"]
    assert {item["id"] for item in mcp["items"]} == {"match-1", "match-2"}


def test_public_search_rejects_bad_cursor_and_oversized_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "public_api.routers.v1.get_content_provider", StubContentReadProvider
    )
    headers = api_headers("invalid_search_key")

    bad_cursor = public.get(
        "/v1/search", params={"cursor": "not-an-offset"}, headers=headers
    )
    oversized = public.get(
        "/v1/search", params={"q": "x" * 201}, headers=headers
    )

    assert bad_cursor.status_code == 400
    assert bad_cursor.json()["detail"]["code"] == "invalid_request"
    assert oversized.status_code == 422


@pytest.mark.parametrize(
    ("error", "status", "code", "retryable"),
    [
        (ProviderUnavailable("L2 timed out"), 503, "l2_unavailable", True),
        (
            ProviderConfigurationError("L2_BASE_URL is missing"),
            503,
            "l2_configuration_error",
            False,
        ),
        (ProviderRequestError("bad cursor"), 400, "invalid_request", None),
    ],
)
def test_public_api_distinguishes_provider_failure_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status: int,
    code: str,
    retryable: bool | None,
) -> None:
    def fail_provider() -> object:
        raise error

    monkeypatch.setattr("public_api.routers.v1.get_content_provider", fail_provider)
    response = public.get("/v1/search", headers=api_headers(f"failure-{code}"))

    assert response.status_code == status
    assert response.json()["detail"]["code"] == code
    if retryable is not None:
        assert response.json()["detail"]["retryable"] is retryable
    if retryable:
        assert response.headers["Retry-After"] == "2"


def test_l2_http_provider_forwards_query_and_maps_bad_request() -> None:
    fixture = StubContentReadProvider().get("cp-001").model_dump(mode="json")
    seen: list[dict[str, list[str]]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            seen.append(query)
            if parsed.path.endswith("/missing"):
                self.send_response(404)
                self.end_headers()
                return
            status_by_query = {"bad": 400, "auth": 401, "missing-route": 404}
            status = status_by_query.get(query.get("q", [""])[0])
            if status is not None:
                self.send_response(status)
                self.end_headers()
                return
            body = (
                {}
                if query.get("q") == ["invalid-schema"]
                else {"items": [fixture], "next_cursor": None, "total": 1}
            )
            payload = json.dumps(body, default=str).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        provider = L2HttpContentReadProvider(
            f"http://127.0.0.1:{server.server_port}", timeout=2
        )
        page = provider.list(limit=1, filters={"q": "Needle", "sort": "score"})
        assert page.total == 1
        with pytest.raises(ProviderRequestError, match="rejected request"):
            provider.list(filters={"q": "bad"})
        with pytest.raises(ProviderConfigurationError, match="authorization failed"):
            provider.list(filters={"q": "auth"})
        with pytest.raises(ProviderUnavailable, match="HTTP 404"):
            provider.list(filters={"q": "missing-route"})
        with pytest.raises(ProviderUnavailable, match="response is invalid"):
            provider.list(filters={"q": "invalid-schema"})
        with pytest.raises(KeyError):
            provider.get("missing")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert seen[0]["q"] == ["Needle"]
    assert seen[0]["sort"] == ["score"]


def test_public_api_launcher_honors_runtime_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    namespace = runpy.run_path(str(root / "scripts" / "run_public_api.py"))
    calls: list[tuple[str, dict[str, object]]] = []

    monkeypatch.setenv("PUBLIC_API_HOST", "127.0.0.2")
    monkeypatch.setenv("PUBLIC_API_PORT", "18001")
    monkeypatch.setenv("PUBLIC_API_RELOAD", "true")
    monkeypatch.setattr(
        uvicorn,
        "run",
        lambda app, **kwargs: calls.append((app, kwargs)),
    )

    namespace["main"]()

    assert calls == [
        (
            "public_api.main:app",
            {"host": "127.0.0.2", "port": 18001, "reload": True},
        )
    ]
