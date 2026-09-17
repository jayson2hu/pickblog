import io
import json
from urllib.error import HTTPError

import pytest
from fastapi.testclient import TestClient

from codepick_l3.provider import L2HttpContentReadProvider, ProviderConfigurationError, ProviderRequestError, StubContentReadProvider
from codepick_l3.public_contract import public_content_item
from reader_api.main import app


def test_public_fields_preserve_method_but_do_not_leak_private_metadata() -> None:
    item = StubContentReadProvider().get("cp-001")
    item.provenance = {
        "scoring_method": "heuristic", "analysis_method": "extractive-v1",
        "translation_available": False, "private_database_url": "must-not-leak",
        "model": "private-model-config", "reviewed": False,
    }
    item.published_at = None
    result = public_content_item(item)
    assert result["published_at"] is None
    assert result["provenance"] == {
        "scoring_method": "heuristic", "analysis_method": "extractive-v1",
        "translation_available": False, "reviewed": False,
    }


@pytest.mark.parametrize("status,body,error", [
    (422, {}, ProviderRequestError),
    (503, {"detail": {"code": "configuration_error"}}, ProviderConfigurationError),
])
def test_provider_keeps_configuration_and_bad_input_distinct(monkeypatch, status, body, error) -> None:
    def fail(*_args, **_kwargs):
        raise HTTPError("http://127.0.0.1/content", status, "test", {}, io.BytesIO(json.dumps(body).encode()))
    monkeypatch.setattr("urllib.request.urlopen", fail)
    with pytest.raises(error):
        L2HttpContentReadProvider("http://127.0.0.1").list()


def test_reader_rejects_oversized_search_before_calling_upstream(monkeypatch) -> None:
    def unexpected():
        raise AssertionError("Invalid request must not call provider")
    monkeypatch.setattr("reader_api.routers.feed.get_content_provider", unexpected)
    assert TestClient(app).get("/api/feed", params={"q": "x" * 201}).status_code == 422
