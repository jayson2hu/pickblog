from datetime import date
from types import SimpleNamespace
from urllib.error import HTTPError
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from codepick_l3.auth import current_user
from codepick_l3.models import Base
from codepick_l3.provider import (
    L2HttpContentReadProvider, ProviderConfigurationError, ProviderRequestError,
    ProviderUnavailable, StubContentReadProvider,
)
from codepick_l3.repository import InMemoryL3Repository, SqlAlchemyL3Repository
from codepick_l3.schemas import User
from reader_api.main import app


@pytest.fixture(params=["memory", "sqlite"])
def boundary(request, tmp_path, monkeypatch):
    engine = None
    session = None
    if request.param == "sqlite":
        engine = create_engine(f"sqlite:///{tmp_path / 'companion.db'}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        session = Session(engine)
        repository = SqlAlchemyL3Repository(session)
    else:
        repository = InMemoryL3Repository()
    user = User(id=199, email="companion-test@example.invalid")
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[current_user] = lambda: user
    for module in ("companion", "me"):
        monkeypatch.setattr(f"reader_api.routers.{module}.get_repository", lambda: repository)
        monkeypatch.setattr(f"reader_api.routers.{module}.has_plan", lambda *a: False)
        monkeypatch.setattr(f"reader_api.routers.{module}.get_settings", lambda: SimpleNamespace(companion_free_daily=5))
    try:
        yield TestClient(app), repository, user
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        if session:
            session.close()
        if engine:
            engine.dispose()


@pytest.mark.parametrize("error,status,retryable", [
    (ProviderUnavailable("connection lost"), 503, True),
    (ProviderConfigurationError("bad config"), 503, False),
    (ProviderRequestError("bad question"), 400, None),
    (KeyError("removed after detail read"), 404, None),
])
@pytest.mark.parametrize("partial", [False, True])
def test_upstream_error_precedes_sse_and_never_charges(boundary, monkeypatch, error, status, retryable, partial):
    client, repository, user = boundary

    class FailingProvider(StubContentReadProvider):
        def companion(self, content_id, question):
            if partial:
                yield "must not leak a partial success"
            raise error

    monkeypatch.setattr("reader_api.routers.companion.get_content_provider", FailingProvider)
    response = client.post("/api/companion", json={"content_id": "cp-001", "question": "why?"})
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/json")
    assert "must not leak" not in response.text
    if retryable is not None:
        assert response.json()["detail"]["retryable"] is retryable
    if retryable:
        assert response.headers["retry-after"] == "2"
    assert repository.get_companion_usage(user.id, date.today()) == 0
    assert client.get("/api/companion/quota").json()["used"] == 0


def test_success_preserves_multiline_sse_and_reports_actual_quota(boundary, monkeypatch):
    client, repository, user = boundary

    class SuccessfulProvider(StubContentReadProvider):
        def companion(self, content_id, question):
            yield "first line\nsecond line"

    monkeypatch.setattr("reader_api.routers.companion.get_content_provider", SuccessfulProvider)
    response = client.post("/api/companion", json={"content_id": "cp-001", "question": "why?"})
    assert response.status_code == 200
    assert response.text == "data: first line\ndata: second line\n\n"
    assert response.headers["X-Companion-Remaining"] == "4"
    assert repository.get_companion_usage(user.id, date.today()) == 1
    assert client.get("/api/companion/quota").json()["used"] == 1
    assert repository.get_companion_usage(user.id + 1, date.today()) == 0


def test_exhausted_quota_does_not_call_upstream_or_increment(boundary, monkeypatch):
    client, repository, user = boundary
    for _ in range(5):
        repository.increment_companion_usage(user.id, date.today())

    class MustNotGenerate(StubContentReadProvider):
        def companion(self, content_id, question):
            raise AssertionError("quota must short circuit generation")

    monkeypatch.setattr("reader_api.routers.companion.get_content_provider", MustNotGenerate)
    response = client.post("/api/companion", json={"content_id": "cp-001", "question": "why?"})
    assert response.status_code == 429
    assert repository.get_companion_usage(user.id, date.today()) == 5


def test_empty_chunks_are_not_success_and_do_not_charge(boundary, monkeypatch):
    client, repository, user = boundary

    class EmptyProvider(StubContentReadProvider):
        def companion(self, content_id, question):
            return iter([])

    monkeypatch.setattr("reader_api.routers.companion.get_content_provider", EmptyProvider)
    response = client.post("/api/companion", json={"content_id": "cp-001", "question": "why?"})
    assert response.status_code == 503
    assert response.json()["detail"]["retryable"] is True
    assert repository.get_companion_usage(user.id, date.today()) == 0


def test_real_http_companion_404_is_missing_content(monkeypatch):
    def unavailable(*args, **kwargs):
        raise HTTPError("http://127.0.0.1/companion", 404, "missing", {}, io.BytesIO(b"{}"))

    monkeypatch.setattr("urllib.request.urlopen", unavailable)
    with pytest.raises(KeyError):
        list(L2HttpContentReadProvider("http://127.0.0.1").companion("6", "why?"))
