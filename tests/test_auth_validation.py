from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from codepick_l3.auth import ALGORITHM
from codepick_l3.config import get_settings
from reader_api.main import app


@pytest.mark.parametrize("claims", [
    {"plan": []}, {"plan": {}}, {"plan": None},
    {"locale": []}, {"locale": {}}, {"locale": None},
    {"sub": "0"}, {"sub": "-1"}, {"sub": "not-an-id"},
    {"exp": float("inf")}, {"exp": None}, {"email": " "},
])
def test_invalid_signed_claims_return_401_without_server_error(claims):
    payload = {
        "sub": "7001", "email": "jwt@example.com", "plan": "free", "locale": "en",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    payload.update(claims)
    token = jwt.encode(payload, get_settings().jwt_secret, algorithm=ALGORITHM)
    with TestClient(app) as client:
        response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid bearer token"
