import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from codepick_l3.billing import sign_webhook
from reader_api.main import app
from reader_api.routers import billing


@pytest.mark.parametrize("payload", [
    {"user_id": 7}, {"user_id": 7, "event": []},
    {"user_id": 7, "event": {"unexpected": True}},
    {"user_id": 7, "event": "unknown"},
    *({"user_id": value, "event": "subscription.activated"}
      for value in [None, True, False, 0, -1, 1.5, [], {}, "invalid"]),
    [], None, "invalid",
])
def test_invalid_signed_webhook_never_changes_subscription(monkeypatch, payload):
    repository = Mock()
    monkeypatch.setattr(billing, "get_repository", lambda: repository)
    raw = json.dumps(payload).encode()
    with TestClient(app) as client:
        response = client.post(
            "/api/billing/webhook", content=raw,
            headers={"X-Paddle-Signature": sign_webhook(raw)},
        )
    assert response.status_code == 422
    repository.set_subscription_plan.assert_not_called()


@pytest.mark.parametrize("raw", [b"{", b"\xff"])
def test_invalid_signed_webhook_json_returns_422(monkeypatch, raw):
    repository = Mock()
    monkeypatch.setattr(billing, "get_repository", lambda: repository)
    with TestClient(app) as client:
        response = client.post(
            "/api/billing/webhook", content=raw,
            headers={"X-Paddle-Signature": sign_webhook(raw)},
        )
    assert response.status_code == 422
    repository.set_subscription_plan.assert_not_called()


def test_webhook_authentication_precedes_payload_validation():
    with TestClient(app) as client:
        response = client.post("/api/billing/webhook", content=b"{")
    assert response.status_code == 401
