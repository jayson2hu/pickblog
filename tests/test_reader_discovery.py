from fastapi.testclient import TestClient

from codepick_l3.provider import StubContentReadProvider
from reader_api.main import app
from public_api.main import app as public_app


def test_api_roots_guide_visitors_to_documentation() -> None:
    for service in (app, public_app):
        client = TestClient(service)
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/docs"
        assert client.get("/docs").status_code == 200
        assert client.get("/does-not-exist").status_code == 404


def test_reader_search_is_applied_before_pagination_and_keeps_provenance(monkeypatch) -> None:
    provider = StubContentReadProvider()
    first = provider._items[0]
    first.title = "Unique real-source article"
    first.provenance = {"scoring_method": "heuristic", "translation_available": False}
    first.language = "en"
    first.reading_minutes = 4
    monkeypatch.setattr("reader_api.routers.feed.get_content_provider", lambda: provider)
    api = TestClient(app)
    page = api.get("/api/feed", params={"q": "Unique real-source", "limit": 1}).json()
    assert page["total"] == 1
    assert page["next_cursor"] is None
    assert page["items"][0]["provenance"]["scoring_method"] == "heuristic"
    assert page["items"][0]["reading_minutes"] == 4
    assert page["items"][0]["language"] == "en"
    assert api.get("/api/feed", params={"q": "no-such-real-article"}).json()["total"] == 0
