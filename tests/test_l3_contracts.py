import asyncio
import importlib.util
import json
import sys
import types
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from codepick_l3.auth import issue_token
from codepick_l3.billing import PaddleBilling, get_billing_client, parse_billing_webhook, sign_webhook
from codepick_l3.briefs import generate_personal_brief, generate_public_brief
from codepick_l3.config import reset_settings_cache
from codepick_l3.email import ConfiguredEmailClient, EmailDeliveryError, get_email_client, mock_email_client
from codepick_l3.models import ApiKeyModel, ApiUsageDailyModel, Base, BookmarkModel, CompanionUsageModel, ReadingEventModel, UserInterestModel, UserModel
from codepick_l3.provider import L2HttpContentReadProvider, ProviderUnavailable, StubContentReadProvider, get_content_provider
from codepick_l3.public_contract import PUBLIC_CONTENT_FIELDS, completed_public_items, public_content_item
from codepick_l3.repository import SqlAlchemyL3Repository, get_repository
from codepick_l3.schemas import ContentDetail, ContentSummary, Page, User
from codepick_l3.usage import hash_key, quota_store, rate_window, require_api_key
from jobs import WorkerSettings, brief_cron_jobs, generate_personal_brief_job, generate_public_brief_job, redis_settings
from public_api.main import app as public_app
from reader_api.main import app as reader_app
import server as mcp_server


reader = TestClient(reader_app)
public = TestClient(public_app)


def load_script_module(name: str):
    from pathlib import Path

    script = Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def token(plan: str = "free") -> str:
    return issue_token(User(id=1, email="dev@example.com", plan=plan))


def test_reader_health_and_protected_route_requires_jwt() -> None:
    assert reader.get("/api/health").status_code == 200
    response = reader.post("/api/events", json={"content_id": "cp-001", "type": "click"})
    assert response.status_code == 401


def test_readiness_reports_independent_dev_defaults(monkeypatch) -> None:
    for key in ["L3_USE_STUB_L2", "L3_REPOSITORY_BACKEND", "L3_QUOTA_BACKEND", "EMAIL_PROVIDER", "BILLING_ENVIRONMENT"]:
        monkeypatch.delenv(key, raising=False)
    reset_settings_cache()
    response = reader.get("/api/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["content_provider"]["mode"] == "stub"
    assert body["checks"]["repository"]["backend"] == "memory"
    assert body["checks"]["quota"]["backend"] == "memory"
    assert body["checks"]["billing"]["environment"] == "sandbox"
    assert body["checks"]["email"]["provider"] == "mock"
    assert public.get("/v1/health").status_code == 200
    assert public.get("/v1/ready").status_code == 401
    assert public.get("/v1/ready", headers={"X-API-Key": "cp_test_key"}).json()["service"] == "public-api"


def test_readiness_reports_missing_final_integration_config(monkeypatch) -> None:
    monkeypatch.setenv("L3_USE_STUB_L2", "false")
    monkeypatch.delenv("L2_BASE_URL", raising=False)
    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "sqlalchemy")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    reset_settings_cache()
    body = reader.get("/api/ready").json()
    assert body["status"] == "degraded"
    assert body["checks"]["content_provider"]["ready"] is False
    assert body["checks"]["repository"]["ready"] is False
    assert body["checks"]["quota"]["ready"] is False
    assert body["checks"]["email"]["ready"] is False
    monkeypatch.setenv("L3_USE_STUB_L2", "true")
    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "memory")
    monkeypatch.setenv("EMAIL_PROVIDER", "mock")
    reset_settings_cache()


def test_readiness_degrades_final_like_defaults_and_requires_email_sender(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "dev-secret")
    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", "dev-webhook-secret")
    monkeypatch.setenv("L3_USE_STUB_L2", "false")
    monkeypatch.setenv("L2_BASE_URL", "https://l2.example.test")
    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "sqlalchemy")
    monkeypatch.setenv("L3_QUOTA_BACKEND", "sqlalchemy")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://codepick:secret@db/codepick_l3")
    monkeypatch.setenv("BILLING_ENVIRONMENT", "production")
    monkeypatch.setenv("PADDLE_CHECKOUT_BASE_URL", "https://sandbox-payments.codepick.local")
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "resend-key")
    monkeypatch.setenv("EMAIL_FROM", "")
    monkeypatch.setenv("L3_AUTH_LOGIN_MODE", "external")
    monkeypatch.setenv("ARQ_REDIS_HOST", "redis")
    monkeypatch.setenv("ARQ_REDIS_PORT", "6379")
    reset_settings_cache()

    body = reader.get("/api/ready").json()
    assert body["status"] == "degraded"
    assert body["checks"]["billing"]["ready"] is False
    assert body["checks"]["email"]["ready"] is False
    assert body["checks"]["secrets"]["ready"] is False

    monkeypatch.setenv("JWT_SECRET", "prod-jwt-secret")
    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", "prod-webhook-secret")
    monkeypatch.setenv("PADDLE_CHECKOUT_BASE_URL", "https://checkout.paddle.com")
    monkeypatch.setenv("EMAIL_FROM", "CodePick <briefs@example.test>")
    reset_settings_cache()

    body = reader.get("/api/ready").json()
    assert body["status"] == "ready"
    assert body["checks"]["billing"]["ready"] is True
    assert body["checks"]["email"]["ready"] is True
    assert body["checks"]["secrets"]["ready"] is True

    monkeypatch.setenv("L3_USE_STUB_L2", "true")
    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "memory")
    monkeypatch.setenv("L3_QUOTA_BACKEND", "memory")
    monkeypatch.setenv("BILLING_ENVIRONMENT", "sandbox")
    monkeypatch.setenv("EMAIL_PROVIDER", "mock")
    reset_settings_cache()


def test_readiness_degrades_final_like_http_l2_and_sqlite_database(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "prod-jwt-secret")
    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", "prod-webhook-secret")
    monkeypatch.setenv("L3_USE_STUB_L2", "false")
    monkeypatch.setenv("L2_BASE_URL", "http://l2.example.test")
    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "sqlalchemy")
    monkeypatch.setenv("L3_QUOTA_BACKEND", "sqlalchemy")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///not-final.db")
    monkeypatch.setenv("BILLING_ENVIRONMENT", "production")
    monkeypatch.setenv("PADDLE_CHECKOUT_BASE_URL", "https://checkout.paddle.com")
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "resend-key")
    monkeypatch.setenv("EMAIL_FROM", "CodePick <briefs@example.test>")
    reset_settings_cache()

    body = reader.get("/api/ready").json()
    assert body["status"] == "degraded"
    assert body["checks"]["content_provider"]["ready"] is False
    assert body["checks"]["repository"]["ready"] is False
    assert body["checks"]["quota"]["ready"] is False

    monkeypatch.setenv("L3_USE_STUB_L2", "true")
    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "memory")
    monkeypatch.setenv("L3_QUOTA_BACKEND", "memory")
    monkeypatch.setenv("BILLING_ENVIRONMENT", "sandbox")
    monkeypatch.setenv("EMAIL_PROVIDER", "mock")
    reset_settings_cache()


def test_readiness_degrades_final_like_http_paddle_checkout(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "prod-jwt-secret")
    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", "prod-webhook-secret")
    monkeypatch.setenv("L3_USE_STUB_L2", "false")
    monkeypatch.setenv("L2_BASE_URL", "https://l2.example.test")
    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "sqlalchemy")
    monkeypatch.setenv("L3_QUOTA_BACKEND", "sqlalchemy")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://codepick:secret@db/codepick_l3")
    monkeypatch.setenv("BILLING_ENVIRONMENT", "production")
    monkeypatch.setenv("PADDLE_CHECKOUT_BASE_URL", "http://checkout.paddle.com")
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "resend-key")
    monkeypatch.setenv("EMAIL_FROM", "CodePick <briefs@example.test>")
    reset_settings_cache()

    body = reader.get("/api/ready").json()
    assert body["status"] == "degraded"
    assert body["checks"]["billing"]["ready"] is False

    monkeypatch.setenv("L3_USE_STUB_L2", "true")
    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "memory")
    monkeypatch.setenv("L3_QUOTA_BACKEND", "memory")
    monkeypatch.setenv("BILLING_ENVIRONMENT", "sandbox")
    monkeypatch.setenv("EMAIL_PROVIDER", "mock")
    reset_settings_cache()


def test_readiness_degrades_final_like_missing_or_invalid_redis(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "prod-jwt-secret")
    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", "prod-webhook-secret")
    monkeypatch.setenv("L3_USE_STUB_L2", "false")
    monkeypatch.setenv("L2_BASE_URL", "https://l2.example.test")
    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "sqlalchemy")
    monkeypatch.setenv("L3_QUOTA_BACKEND", "sqlalchemy")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://codepick:secret@db/codepick_l3")
    monkeypatch.setenv("BILLING_ENVIRONMENT", "production")
    monkeypatch.setenv("PADDLE_CHECKOUT_BASE_URL", "https://checkout.paddle.com")
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "resend-key")
    monkeypatch.setenv("EMAIL_FROM", "CodePick <briefs@example.test>")
    monkeypatch.delenv("ARQ_REDIS_HOST", raising=False)
    monkeypatch.delenv("ARQ_REDIS_PORT", raising=False)
    reset_settings_cache()

    body = reader.get("/api/ready").json()
    assert body["status"] == "degraded"
    assert body["checks"]["worker"]["ready"] is False

    monkeypatch.setenv("ARQ_REDIS_HOST", "redis")
    monkeypatch.setenv("ARQ_REDIS_PORT", "not-a-port")
    body = reader.get("/api/ready").json()
    assert body["status"] == "degraded"
    assert body["checks"]["worker"]["ready"] is False
    assert body["checks"]["worker"]["redis_port"] is None

    monkeypatch.setenv("L3_USE_STUB_L2", "true")
    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "memory")
    monkeypatch.setenv("L3_QUOTA_BACKEND", "memory")
    monkeypatch.setenv("BILLING_ENVIRONMENT", "sandbox")
    monkeypatch.setenv("EMAIL_PROVIDER", "mock")
    monkeypatch.setenv("ARQ_REDIS_PORT", "6379")
    reset_settings_cache()


def test_require_plan_blocks_free_user_from_personal_brief() -> None:
    response = reader.get("/api/brief/me", headers={"Authorization": f"Bearer {token('free')}"})
    assert response.status_code == 403


def test_require_plan_allows_pro_user_for_personal_brief() -> None:
    get_repository().set_subscription_plan(1, "pro")
    response = reader.get("/api/brief/me", headers={"Authorization": f"Bearer {token('pro')}"})
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == 1
    assert body["items"]
    get_repository().set_subscription_plan(1, "free")


def test_require_plan_uses_subscription_state_not_client_claim() -> None:
    get_repository().set_subscription_plan(1, "free")
    forged_pro = token("pro")
    response = reader.get("/api/brief/me", headers={"Authorization": f"Bearer {forged_pro}"})
    assert response.status_code == 403
    get_repository().set_subscription_plan(1, "pro")
    response = reader.get("/api/brief/me", headers={"Authorization": f"Bearer {token('free')}"})
    assert response.status_code == 200
    get_repository().set_subscription_plan(1, "free")


def test_reader_routes_do_not_scatter_direct_plan_checks() -> None:
    from pathlib import Path

    routes_dir = Path(__file__).resolve().parents[1] / "services" / "reader-api" / "reader_api" / "routers"
    direct_checks: list[str] = []
    for path in routes_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "user.plan ==" in text or "user.plan !=" in text:
            direct_checks.append(path.name)
    assert direct_checks == []


def test_login_ignores_client_supplied_plan_and_uses_subscription_state() -> None:
    get_repository().set_subscription_plan(1, "free")
    response = reader.post("/api/auth/login", json={"email": "dev@example.com", "locale": "en", "plan": "pro"})
    assert response.status_code == 200
    assert response.json()["user"]["plan"] == "free"
    get_repository().set_subscription_plan(1, "pro")
    response = reader.post("/api/auth/login", json={"email": "dev@example.com", "locale": "en"})
    assert response.status_code == 200
    assert response.json()["user"]["plan"] == "pro"
    get_repository().set_subscription_plan(1, "free")


def test_development_login_uses_stable_distinct_user_identities() -> None:
    first = reader.post("/api/auth/login", json={"email": "isolation-a@example.com", "locale": "en"})
    second = reader.post("/api/auth/login", json={"email": "isolation-b@example.com", "locale": "zh"})
    repeated = reader.post("/api/auth/login", json={"email": "ISOLATION-A@example.com", "locale": "zh"})

    assert first.status_code == second.status_code == repeated.status_code == 200
    first_user = first.json()["user"]
    second_user = second.json()["user"]
    assert first_user["id"] != second_user["id"]
    assert repeated.json()["user"]["id"] == first_user["id"]
    assert repeated.json()["user"]["email"] == "isolation-a@example.com"
    assert repeated.json()["user"]["locale"] == "zh"


def test_external_auth_mode_disables_unverified_email_login(monkeypatch) -> None:
    monkeypatch.setenv("L3_AUTH_LOGIN_MODE", "external")
    reset_settings_cache()
    response = reader.post("/api/auth/login", json={"email": "anyone@example.com", "locale": "en"})
    assert response.status_code == 503
    assert response.json()["detail"] == "development email login is disabled"
    assert reader.get("/api/ready").json()["checks"]["auth"] == {"login_mode": "external", "ready": True}
    monkeypatch.setenv("L3_AUTH_LOGIN_MODE", "development")
    reset_settings_cache()


def test_jwt_rejects_tampered_expired_and_malformed_tokens() -> None:
    valid = issue_token(User(id=7001, email="jwt@example.com", plan="free"))
    header, payload, signature = valid.split(".")
    tampered_signature = ("A" if signature[0] != "A" else "B") + signature[1:]
    expired = issue_token(User(id=7001, email="jwt@example.com", plan="free"), expires_delta=timedelta(seconds=-1))

    for candidate in [f"{header}.{payload}.{tampered_signature}", expired, "not-a-jwt"]:
        response = reader.get("/api/me", headers={"Authorization": f"Bearer {candidate}"})
        assert response.status_code == 401
        assert response.json()["detail"] == "invalid bearer token"


def test_two_users_cannot_see_or_mutate_each_others_account_state() -> None:
    first = reader.post("/api/auth/login", json={"email": "tenant-a@example.com", "locale": "en"}).json()
    second = reader.post("/api/auth/login", json={"email": "tenant-b@example.com", "locale": "en"}).json()
    first_id = first["user"]["id"]
    second_id = second["user"]["id"]
    first_headers = {"Authorization": f"Bearer {first['token']}"}
    second_headers = {"Authorization": f"Bearer {second['token']}"}
    assert first_id != second_id

    first_tags = ["ai", "backend", "python", "postgres", "agents"]
    second_tags = ["data", "infra", "product", "security", "testing"]
    assert reader.post("/api/interests", json={"tags": first_tags}, headers=first_headers).status_code == 200
    assert reader.post("/api/interests", json={"tags": second_tags}, headers=second_headers).status_code == 200
    assert set(reader.get("/api/interests", headers=first_headers).json()["tags"]) == set(first_tags)
    assert set(reader.get("/api/interests", headers=second_headers).json()["tags"]) == set(second_tags)

    assert reader.post(
        "/api/bookmarks",
        json={"content_id": "cp-001", "note": "tenant-a-only", "highlights": ["a"]},
        headers=first_headers,
    ).status_code == 200
    assert reader.post(
        "/api/bookmarks",
        json={"content_id": "cp-001", "note": "tenant-b-only", "highlights": ["b"]},
        headers=second_headers,
    ).status_code == 200
    assert [item["note"] for item in reader.get("/api/bookmarks", headers=first_headers).json()["items"]] == ["tenant-a-only"]
    assert [item["note"] for item in reader.get("/api/bookmarks", headers=second_headers).json()["items"]] == ["tenant-b-only"]

    assert reader.post("/api/events", json={"content_id": "cp-001", "type": "click"}, headers=first_headers).status_code == 200
    first_event = reader.post("/api/events", json={"content_id": "cp-001", "type": "deep_read"}, headers=first_headers)
    second_event = reader.post("/api/events", json={"content_id": "cp-001", "type": "click"}, headers=second_headers)
    assert first_event.json()["north_star"]["reading_events_total"] == 3
    assert second_event.json()["north_star"]["reading_events_total"] == 2
    assert first_event.json()["north_star"]["deep_read_closed_loop_events"] == 2
    assert second_event.json()["north_star"]["deep_read_closed_loop_events"] == 1

    first_follow = reader.post("/api/follow", json={"target_type": "source", "target_id": "tenant-a-source"}, headers=first_headers).json()
    second_follow = reader.post("/api/follow", json={"target_type": "source", "target_id": "tenant-b-source"}, headers=second_headers).json()
    assert {item["target_id"] for item in first_follow["follows"]} == {"tenant-a-source"}
    assert {item["target_id"] for item in second_follow["follows"]} == {"tenant-b-source"}

    repo = get_repository()
    repo.set_subscription_plan(first_id, "pro")
    repo.set_subscription_plan(second_id, "free")
    assert reader.get("/api/me", headers=first_headers).json()["plan"] == "pro"
    assert reader.get("/api/me", headers=second_headers).json()["plan"] == "free"

    first_key = reader.post("/api/api-keys", json={"scopes": ["read"]}, headers=first_headers).json()
    second_key = reader.post("/api/api-keys", json={"scopes": ["read"]}, headers=second_headers).json()
    first_keys = reader.get("/api/api-keys", headers=first_headers).json()["items"]
    second_keys = reader.get("/api/api-keys", headers=second_headers).json()["items"]
    assert first_key["prefix"] in {item["prefix"] for item in first_keys}
    assert second_key["prefix"] not in {item["prefix"] for item in first_keys}
    assert second_key["prefix"] in {item["prefix"] for item in second_keys}
    assert first_key["prefix"] not in {item["prefix"] for item in second_keys}

    forbidden_revoke = reader.delete(f"/api/api-keys/{first_key['prefix']}", headers=second_headers)
    assert forbidden_revoke.status_code == 404
    assert public.get("/v1/today", headers={"X-API-Key": first_key["key"]}).status_code == 200
    first_usage = reader.get("/api/api-keys/usage", headers=first_headers).json()["days"]
    second_usage = reader.get("/api/api-keys/usage", headers=second_headers).json()["days"]
    assert sum(day["count"] for day in first_usage) == 1
    assert sum(day["count"] for day in second_usage) == 0


def test_stub_provider_returns_completed_fixture_and_detail_translation() -> None:
    provider = StubContentReadProvider()
    page = provider.list(limit=1)
    assert page.total >= 1
    assert page.items[0].status == "COMPLETED"
    detail = provider.get(page.items[0].id)
    assert "zh" in detail.translations


def test_content_provider_cursor_pagination_is_stable_without_duplicates() -> None:
    provider = StubContentReadProvider()
    first = provider.list(limit=1, filters={"sort": "published_at"})
    assert first.next_cursor is not None
    second = provider.list(cursor=first.next_cursor, limit=1, filters={"sort": "published_at"})
    assert second.items
    assert first.items[0].id != second.items[0].id
    assert second.next_cursor is None


def test_public_api_requires_api_key() -> None:
    response = public.get("/v1/today")
    assert response.status_code == 401


def test_public_api_ready_requires_api_key() -> None:
    assert public.get("/v1/ready").status_code == 401
    assert public.get("/v1/ready", headers={"X-API-Key": "cp_test_key"}).status_code == 200


def test_public_api_ready_authenticates_without_consuming_quota() -> None:
    record = quota_store.add_key("ready_key", daily_quota=1, rpm=1)
    assert public.get("/v1/ready", headers={"X-API-Key": "ready_key"}).status_code == 200
    assert public.get("/v1/ready", headers={"X-API-Key": "ready_key"}).status_code == 200
    assert (record.key_hash, date.today()) not in quota_store.daily
    assert record.key_hash not in rate_window.minute


def test_public_api_ready_rejects_key_without_read_scope() -> None:
    record = quota_store.add_key("ready_write_only_key", daily_quota=20, rpm=20)
    record.scopes = ["write"]
    response = public.get("/v1/ready", headers={"X-API-Key": "ready_write_only_key"})
    assert response.status_code == 403
    assert response.json()["detail"] == "read scope required"


def test_public_api_does_not_import_internal_reader_auth_or_repository_state() -> None:
    from pathlib import Path

    public_api = Path(__file__).resolve().parents[1] / "services" / "public-api" / "public_api"
    combined = "\n".join(path.read_text(encoding="utf-8") for path in public_api.rglob("*.py"))
    forbidden = ["current_user", "require_plan", "get_repository", "Authorization", "Bearer", "reader_api"]
    for marker in forbidden:
        assert marker not in combined
    assert "require_api_key" in combined


def test_public_api_returns_trimmed_schema_without_private_context() -> None:
    response = public.get("/v1/today", headers={"X-API-Key": "cp_test_key"})
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert set(item) == PUBLIC_CONTENT_FIELDS
    assert "base_analysis" not in item
    assert "translations" not in item
    assert "scores" in item
    assert "quota" in response.json()


def test_public_api_content_endpoints_return_exact_public_contract() -> None:
    headers = {"X-API-Key": "cp_test_key"}
    today_response = public.get("/v1/today", headers=headers)
    assert today_response.status_code == 200
    content_id = today_response.json()["items"][0]["id"]

    search_response = public.get("/v1/search", params={"q": "MCP"}, headers=headers)
    item_response = public.get(f"/v1/items/{content_id}", headers=headers)
    trending_response = public.get("/v1/trending", headers=headers)

    assert search_response.status_code == 200
    assert item_response.status_code == 200
    assert trending_response.status_code == 200
    for response in [today_response, search_response, item_response, trending_response]:
        assert response.json()["quota"]["daily"] > 0
        assert response.json()["quota"]["rate_limit_rpm"] > 0
    for item in [*today_response.json()["items"], *search_response.json()["items"], *trending_response.json()["items"], item_response.json()["item"]]:
        assert set(item) == PUBLIC_CONTENT_FIELDS


def test_public_api_taxonomy_endpoints_include_quota_context() -> None:
    headers = {"X-API-Key": "cp_test_key"}
    sources_response = public.get("/v1/sources", headers=headers)
    verticals_response = public.get("/v1/verticals", headers=headers)

    assert sources_response.status_code == 200
    assert verticals_response.status_code == 200
    assert sources_response.json()["sources"]
    assert verticals_response.json()["verticals"]
    for response in [sources_response, verticals_response]:
        assert response.json()["quota"]["daily"] > 0
        assert response.json()["quota"]["rate_limit_rpm"] > 0


def test_redesign_me_taxonomy_companion_quota_and_public_taxonomy() -> None:
    headers = {"Authorization": f"Bearer {token('free')}"}
    me_response = reader.get("/api/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["audience_code"] == "general"
    assert me_response.json()["is_admin"] is False

    taxonomy_response = reader.get("/api/taxonomy", headers=headers)
    assert taxonomy_response.status_code == 200
    taxonomy_body = taxonomy_response.json()
    assert taxonomy_body["categories"]
    assert taxonomy_body["audience"]["code"] == "general"
    assert taxonomy_body["audience"]["categories"]

    quota_response = reader.get("/api/companion/quota", headers=headers)
    assert quota_response.status_code == 200
    assert quota_response.json()["limit"] == 5
    assert quota_response.json()["unlimited"] is False

    public_taxonomy = public.get("/v1/taxonomy", headers={"X-API-Key": "cp_test_key"})
    assert public_taxonomy.status_code == 200
    public_body = public_taxonomy.json()
    assert set(public_body) == {"categories", "audiences", "quota"}
    assert set(public_body["categories"][0]) == {"code", "label"}
    assert "color_from" not in public_body["categories"][0]


def test_taxonomy_admin_crud_audience_assignment_and_public_boundary() -> None:
    from codepick_l3.repository import repository

    repository.user_profiles[1] = {"id": 1, "email": "admin@example.com", "nickname": "admin", "locale": "en", "is_admin": True, "audience_code": "general"}
    admin_headers = {"Authorization": f"Bearer {token('free')}"}

    response = reader.post(
        "/api/admin/categories",
        headers=admin_headers,
        json={"code": "ops", "label_en": "Operations", "label_zh": "运营", "color_from": "#111827", "color_to": "#4f46e5"},
    )
    assert response.status_code == 200
    assert response.json()["category"]["code"] == "ops"

    response = reader.post("/api/admin/audiences", headers=admin_headers, json={"code": "operators", "label_en": "Operators", "label_zh": "运营者"})
    assert response.status_code == 200

    response = reader.put("/api/admin/audiences/operators/categories", headers=admin_headers, json={"categories": ["ops"]})
    assert response.status_code == 200
    assert response.json()["audience"]["categories"] == ["ops"]

    response = reader.patch("/api/me/audience", headers=admin_headers, json={"audience_code": "operators"})
    assert response.status_code == 200
    taxonomy_response = reader.get("/api/taxonomy", headers=admin_headers)
    assert [category["code"] for category in taxonomy_response.json()["categories"]] == ["ops"]

    public_taxonomy = public.get("/v1/taxonomy", headers={"X-API-Key": "cp_test_key"}).json()
    assert {"code", "label"} == set(public_taxonomy["categories"][0])
    assert "label_en" not in public_taxonomy["categories"][0]

    repository.user_profiles[2] = {"id": 2, "email": "user@example.com", "nickname": "user", "locale": "en", "is_admin": False, "audience_code": "general"}
    non_admin_token = issue_token(User(id=2, email="user@example.com", plan="free"))
    assert reader.post("/api/admin/categories", headers={"Authorization": f"Bearer {non_admin_token}"}, json={"code": "x"}).status_code == 403


def test_public_api_taxonomy_filters_non_completed_content(monkeypatch) -> None:
    completed = StubContentReadProvider().get("cp-001")
    draft = completed.model_copy(update={"id": "cp-draft", "source": "Draft Source", "vertical": "draft", "status": "DRAFT"})

    class MixedTaxonomyProvider:
        def list(self, *args, **kwargs) -> Page:
            return Page(
                items=[
                    ContentSummary.model_validate(completed.model_dump()),
                    ContentSummary.model_validate(draft.model_dump()),
                ],
                next_cursor=None,
                total=2,
            )

    monkeypatch.setattr("public_api.routers.v1.get_content_provider", lambda: MixedTaxonomyProvider())

    headers = {"X-API-Key": "cp_test_key"}
    sources_response = public.get("/v1/sources", headers=headers)
    verticals_response = public.get("/v1/verticals", headers=headers)

    assert sources_response.status_code == 200
    assert verticals_response.status_code == 200
    assert "Draft Source" not in sources_response.json()["sources"]
    assert "draft" not in verticals_response.json()["verticals"]


def test_public_api_today_cursor_paginates_without_duplicates() -> None:
    headers = {"X-API-Key": "cp_test_key"}
    first = public.get("/v1/today", params={"limit": 1}, headers=headers)
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["next_cursor"] is not None

    second = public.get("/v1/today", params={"limit": 1, "cursor": first_body["next_cursor"]}, headers=headers)
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["items"]
    assert first_body["items"][0]["id"] != second_body["items"][0]["id"]
    assert second_body["next_cursor"] is None


def test_public_api_rejects_out_of_range_limits() -> None:
    headers = {"X-API-Key": "cp_test_key"}
    for path, params in [
        ("/v1/today", {"limit": 0}),
        ("/v1/today", {"limit": 51}),
        ("/v1/search", {"q": "MCP", "limit": 0}),
        ("/v1/search", {"q": "MCP", "limit": 51}),
    ]:
        response = public.get(path, params=params, headers=headers)
        assert response.status_code == 422


def test_reader_feed_rejects_out_of_range_limits() -> None:
    assert reader.get("/api/feed", params={"limit": 0}).status_code == 422
    assert reader.get("/api/feed", params={"limit": 51}).status_code == 422


def test_reader_api_filters_or_rejects_non_completed_content(monkeypatch) -> None:
    completed = StubContentReadProvider().get("cp-001")
    draft = completed.model_copy(update={"id": "cp-draft", "status": "DRAFT"})

    class MixedStatusProvider:
        def list(self, *args, **kwargs) -> Page:
            return Page(
                items=[
                    ContentSummary.model_validate(completed.model_dump()),
                    ContentSummary.model_validate(draft.model_dump()),
                ],
                next_cursor=None,
                total=2,
            )

        def get(self, content_id: str) -> ContentDetail:
            if content_id == "cp-draft":
                return draft
            return completed

        def recommend(self, *args, **kwargs):
            return [
                ContentSummary.model_validate(completed.model_dump()),
                ContentSummary.model_validate(draft.model_dump()),
            ]

    provider = MixedStatusProvider()
    monkeypatch.setattr("reader_api.routers.feed.get_content_provider", lambda: provider)
    monkeypatch.setattr("reader_api.routers.read.get_content_provider", lambda: provider)
    monkeypatch.setattr("reader_api.routers.library.get_content_provider", lambda: provider)

    feed_response = reader.get("/api/feed")
    assert feed_response.status_code == 200
    assert [item["id"] for item in feed_response.json()["items"]] == ["cp-001"]

    assert reader.get("/api/read/cp-draft").status_code == 404

    headers = {"Authorization": f"Bearer {token('free')}"}
    bookmark_response = reader.post("/api/bookmarks", json={"content_id": "cp-draft"}, headers=headers)
    assert bookmark_response.status_code == 404

    recommendations_response = reader.get("/api/recommendations", headers=headers)
    assert recommendations_response.status_code == 200
    assert [item["id"] for item in recommendations_response.json()["items"]] == ["cp-001"]


def test_reader_events_reject_non_completed_content_before_north_star_mutation(monkeypatch) -> None:
    draft = StubContentReadProvider().get("cp-001").model_copy(update={"id": "cp-draft", "status": "DRAFT"})

    class DraftEventProvider:
        def get(self, content_id: str) -> ContentDetail:
            assert content_id == "cp-draft"
            return draft

    repo = get_repository()
    before = dict(repo.north_star())
    monkeypatch.setattr("reader_api.routers.events.get_content_provider", lambda: DraftEventProvider())

    response = reader.post(
        "/api/events",
        json={"content_id": "cp-draft", "type": "deep_read"},
        headers={"Authorization": f"Bearer {token('free')}"},
    )

    assert response.status_code == 404
    assert repo.north_star() == before


def test_reader_events_reject_unknown_event_type_before_north_star_mutation() -> None:
    repo = get_repository()
    before = dict(repo.north_star())

    response = reader.post(
        "/api/events",
        json={"content_id": "cp-001", "type": "reading_time"},
        headers={"Authorization": f"Bearer {token('free')}"},
    )

    assert response.status_code == 422
    assert repo.north_star() == before


def test_public_contract_serializer_is_single_source_for_v1_and_mcp() -> None:
    detail = StubContentReadProvider().get("cp-001")
    serialized = public_content_item(detail)
    assert set(serialized) == PUBLIC_CONTENT_FIELDS
    assert "base_analysis" not in serialized
    assert "translations" not in serialized
    assert "status" not in serialized


def test_public_contract_rejects_non_completed_content() -> None:
    detail = StubContentReadProvider().get("cp-001").model_copy(update={"status": "DRAFT"})
    assert completed_public_items([detail]) == []
    with pytest.raises(ValueError, match="public content must be COMPLETED"):
        public_content_item(detail)


def test_public_api_daily_quota_rejects_after_limit() -> None:
    quota_store.add_key("tiny_key", daily_quota=1, rpm=20)
    assert public.get("/v1/today", headers={"X-API-Key": "tiny_key"}).status_code == 200
    response = public.get("/v1/today", headers={"X-API-Key": "tiny_key"})
    assert response.status_code == 429
    detail = response.json()["detail"]
    assert detail["error"] == "daily_quota_exceeded"
    assert detail["reset_seconds"] == 86400


def test_public_api_today_counts_one_quota_unit_per_request() -> None:
    record = quota_store.add_key("single_count_key", daily_quota=1, rpm=20)
    response = public.get("/v1/today", headers={"X-API-Key": "single_count_key"})

    assert response.status_code == 200
    assert quota_store.daily[(record.key_hash, date.today())] == 1


def test_reader_api_key_usage_returns_seven_day_window() -> None:
    owner_id = 777
    record = quota_store.add_key("usage_window_key", owner_user_id=owner_id, daily_quota=20, rpm=20)
    quota_store.daily[(record.key_hash, date.today())] = 3
    quota_store.daily[(record.key_hash, date.today() - timedelta(days=2))] = 5

    usage_token = issue_token(User(id=owner_id, email="usage@example.com", plan="free"))
    response = reader.get("/api/api-keys/usage", headers={"Authorization": f"Bearer {usage_token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["window"] == 7
    assert len(body["days"]) == 7
    counts = {entry["day"]: entry["count"] for entry in body["days"]}
    assert counts[date.today().isoformat()] == 3
    assert counts[(date.today() - timedelta(days=2)).isoformat()] == 5
    assert reader.get("/api/api-keys/usage").status_code == 401


def test_public_api_rate_limit_rejects_after_rpm() -> None:
    quota_store.add_key("slow_key", daily_quota=20, rpm=1)
    assert public.get("/v1/today", headers={"X-API-Key": "slow_key"}).status_code == 200
    response = public.get("/v1/today", headers={"X-API-Key": "slow_key"})
    assert response.status_code == 429
    detail = response.json()["detail"]
    assert detail["error"] == "rate_limit_exceeded"
    assert 1 <= detail["reset_seconds"] <= 60


def test_public_api_rate_limit_resets_on_new_minute(monkeypatch) -> None:
    quota_store.add_key("window_key", daily_quota=20, rpm=1)
    monkeypatch.setattr("codepick_l3.usage.time.time", lambda: 120.0)
    assert public.get("/v1/today", headers={"X-API-Key": "window_key"}).status_code == 200
    response = public.get("/v1/today", headers={"X-API-Key": "window_key"})
    assert response.status_code == 429
    monkeypatch.setattr("codepick_l3.usage.time.time", lambda: 181.0)
    assert public.get("/v1/today", headers={"X-API-Key": "window_key"}).status_code == 200


def test_reader_api_key_lifecycle_is_jwt_scoped_and_public_api_compatible() -> None:
    assert reader.get("/api/api-keys").status_code == 401
    headers = {"Authorization": f"Bearer {token('free')}"}
    created = reader.post("/api/api-keys", json={"scopes": ["read"]}, headers=headers)
    assert created.status_code == 200
    body = created.json()
    raw_key = body["key"]
    assert raw_key.startswith("cp_")
    assert body["status"] == "active"

    listed = reader.get("/api/api-keys", headers=headers)
    assert listed.status_code == 200
    listed_key = next(item for item in listed.json()["items"] if item["prefix"] == body["prefix"])
    assert listed_key["prefix"] == body["prefix"]
    assert "key" not in listed_key

    public_response = public.get("/v1/today", headers={"X-API-Key": raw_key})
    assert public_response.status_code == 200

    revoked = reader.delete(f"/api/api-keys/{body['prefix']}", headers=headers)
    assert revoked.status_code == 200
    rejected = public.get("/v1/today", headers={"X-API-Key": raw_key})
    assert rejected.status_code == 401


def test_reader_api_key_creation_rejects_non_read_scopes() -> None:
    headers = {"Authorization": f"Bearer {token('free')}"}
    for scopes in [["write"], ["read", "read"], ["read", "write"]]:
        response = reader.post("/api/api-keys", json={"scopes": scopes}, headers=headers)
        assert response.status_code == 422
        assert "public api keys only support read scope" in str(response.json())


def test_public_api_rejects_key_without_read_scope() -> None:
    record = quota_store.add_key("write_only_key", daily_quota=20, rpm=20)
    record.scopes = ["write"]
    response = public.get("/v1/today", headers={"X-API-Key": "write_only_key"})
    assert response.status_code == 403
    assert response.json()["detail"] == "read scope required"


def test_webhook_signature_updates_subscription_state() -> None:
    payload = {"user_id": 7, "event": "subscription.activated"}
    raw = json.dumps(payload).encode("utf-8")
    response = reader.post("/api/billing/webhook", content=raw, headers={"X-Paddle-Signature": sign_webhook(raw)})
    assert response.status_code == 200
    assert response.json()["plan"] == "pro"
    assert get_repository().get_subscription_plan(7) == "pro"


def test_paddle_style_webhook_custom_data_updates_subscription_state() -> None:
    payload = {"event_type": "transaction.completed", "data": {"custom_data": {"user_id": "8"}}}
    raw = json.dumps(payload).encode("utf-8")
    response = reader.post("/api/billing/webhook", content=raw, headers={"X-Paddle-Signature": sign_webhook(raw)})
    assert response.status_code == 200
    assert response.json()["event"] == "transaction.completed"
    assert response.json()["plan"] == "pro"
    assert get_repository().get_subscription_plan(8) == "pro"


def test_paddle_cancellation_webhook_downgrades_subscription() -> None:
    get_repository().set_subscription_plan(8, "pro")
    payload = {"event_type": "subscription.canceled", "data": {"custom_data": {"user_id": 8}}}
    raw = json.dumps(payload).encode("utf-8")
    response = reader.post("/api/billing/webhook", content=raw, headers={"X-Paddle-Signature": sign_webhook(raw)})
    assert response.status_code == 200
    assert response.json()["plan"] == "free"
    assert get_repository().get_subscription_plan(8) == "free"


def test_signed_webhook_rejects_missing_user_id_and_unknown_event() -> None:
    missing_user = {"event_type": "transaction.completed", "data": {"custom_data": {}}}
    raw = json.dumps(missing_user).encode("utf-8")
    response = reader.post("/api/billing/webhook", content=raw, headers={"X-Paddle-Signature": sign_webhook(raw)})
    assert response.status_code == 422

    unknown_event = {"user_id": 9, "event": "payment.refunded"}
    raw = json.dumps(unknown_event).encode("utf-8")
    response = reader.post("/api/billing/webhook", content=raw, headers={"X-Paddle-Signature": sign_webhook(raw)})
    assert response.status_code == 422


def test_webhook_bad_signature_rejected() -> None:
    response = reader.post("/api/billing/webhook", json={"user_id": 7}, headers={"X-Paddle-Signature": "bad"})
    assert response.status_code == 401


def test_checkout_accepts_supported_usd_cadences_and_rejects_unknown() -> None:
    headers = {"Authorization": f"Bearer {token('free')}"}
    for cadence in ["month", "year", "earlybird"]:
        response = reader.post("/api/billing/checkout", json={"cadence": cadence}, headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["currency"] == "USD"
        assert f"cadence={cadence}" in body["checkout_url"]
        assert "currency=USD" in body["checkout_url"]

    response = reader.post("/api/billing/checkout", json={"cadence": "weekly"}, headers=headers)
    assert response.status_code == 422


def test_companion_free_quota_and_pro_unlimited_behavior() -> None:
    for _ in range(5):
        response = reader.post(
            "/api/companion",
            json={"content_id": "cp-001", "question": "Why does this matter?"},
            headers={"Authorization": f"Bearer {token('free')}"},
        )
        assert response.status_code == 200
        assert response.headers["X-Companion-Limit"] == "5"
        assert "X-Companion-Remaining" in response.headers
    response = reader.post(
        "/api/companion",
        json={"content_id": "cp-001", "question": "Again?"},
        headers={"Authorization": f"Bearer {token('free')}"},
    )
    assert response.status_code == 429

    get_repository().set_subscription_plan(1, "pro")
    response = reader.post(
        "/api/companion",
        json={"content_id": "cp-001", "question": "Again?"},
        headers={"Authorization": f"Bearer {token('pro')}"},
    )
    assert response.status_code == 200
    assert response.headers["X-Companion-Unlimited"] == "true"
    assert response.headers["X-Companion-Remaining"] == "-1"
    get_repository().set_subscription_plan(1, "free")


def test_companion_streaming_contract_is_preserved() -> None:
    from pathlib import Path

    get_repository().set_subscription_plan(1, "pro")
    response = reader.post(
        "/api/companion",
        json={"content_id": "cp-001", "question": "Why does this matter?"},
        headers={"Authorization": f"Bearer {token('pro')}"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "data:" in response.text

    widget = (Path(__file__).resolve().parents[1] / "apps" / "reader-web" / "components" / "CompanionWidget.tsx").read_text(encoding="utf-8")
    assert ".body?.getReader()" in widget
    assert "reader.read()" in widget
    assert "response.text()" not in widget
    get_repository().set_subscription_plan(1, "free")


def test_companion_rejects_non_completed_content_before_usage(monkeypatch) -> None:
    draft = StubContentReadProvider().get("cp-001").model_copy(update={"id": "cp-draft", "status": "DRAFT"})

    class DraftCompanionProvider:
        def get(self, content_id: str) -> ContentDetail:
            assert content_id == "cp-draft"
            return draft

        def companion(self, *args, **kwargs):
            raise AssertionError("companion stream should not start for non-completed content")

    repo = get_repository()
    usage_key = (1, date.today())
    before = getattr(repo, "companion_usage", {}).get(usage_key, 0)
    monkeypatch.setattr("reader_api.routers.companion.get_content_provider", lambda: DraftCompanionProvider())

    response = reader.post(
        "/api/companion",
        json={"content_id": "cp-draft", "question": "Why does this matter?"},
        headers={"Authorization": f"Bearer {token('free')}"},
    )

    assert response.status_code == 404
    assert getattr(repo, "companion_usage", {}).get(usage_key, 0) == before


def test_public_brief_generation_deduplicates_quality_items() -> None:
    brief = generate_public_brief(StubContentReadProvider())
    ids = [item.id for item in brief.items]
    assert ids
    assert len(ids) == len(set(ids))
    assert all(item.scores["quality"] >= 80 for item in brief.items)


def test_brief_generation_filters_non_completed_content() -> None:
    completed = StubContentReadProvider().get("cp-001")
    draft = completed.model_copy(update={"id": "cp-draft", "status": "DRAFT"})
    completed_summary = ContentSummary.model_validate(completed.model_dump())
    draft_summary = ContentSummary.model_validate(draft.model_dump())

    class MixedStatusBriefProvider:
        def list(self, *args, **kwargs) -> Page:
            return Page(items=[completed_summary, draft_summary], next_cursor=None, total=2)

        def recommend(self, *args, **kwargs):
            return [completed_summary, draft_summary]

    provider = MixedStatusBriefProvider()
    public_brief = generate_public_brief(provider)
    personal_brief = generate_personal_brief(provider, User(id=7, email="pro@example.com", plan="pro"))

    assert [item.id for item in public_brief.items] == ["cp-001"]
    assert [item.id for item in personal_brief.items] == ["cp-001"]


def test_interest_onboarding_requires_jwt_and_accepts_5_to_8_tags() -> None:
    payload = {"tags": ["ai", "backend", "python", "postgres", "agents"]}
    assert reader.post("/api/interests", json=payload).status_code == 401
    response = reader.post("/api/interests", json=payload, headers={"Authorization": f"Bearer {token('free')}"})
    assert response.status_code == 200
    assert response.json()["count"] == 5
    saved = reader.get("/api/interests", headers={"Authorization": f"Bearer {token('free')}"})
    assert saved.json()["tags"]["ai"] == 1


def test_interest_onboarding_rejects_too_few_tags() -> None:
    response = reader.post("/api/interests", json={"tags": ["ai"]}, headers={"Authorization": f"Bearer {token('free')}"})
    assert response.status_code == 422


def test_follow_bookmark_and_recommendation_routes_are_jwt_scoped() -> None:
    headers = {"Authorization": f"Bearer {token('free')}"}
    follow = reader.post("/api/follow", json={"target_type": "source", "target_id": "CodePick Research"}, headers=headers)
    assert follow.status_code == 200
    bookmark = reader.post("/api/bookmarks", json={"content_id": "cp-001", "note": "review later", "highlights": ["queue"]}, headers=headers)
    assert bookmark.status_code == 200
    assert bookmark.json()["north_star"]["deep_read_closed_loop_events"] >= 1
    assert reader.get("/api/bookmarks", headers=headers).json()["items"][0]["content_id"] == "cp-001"
    recommendations = reader.get("/api/recommendations", headers=headers)
    assert recommendations.status_code == 200
    assert recommendations.json()["items"][0]["id"] == "cp-001"


def test_reading_event_records_north_star_closed_loop_only() -> None:
    headers = {"Authorization": f"Bearer {token('free')}"}
    click = reader.post("/api/events", json={"content_id": "cp-001", "type": "click"}, headers=headers)
    bookmark = reader.post("/api/events", json={"content_id": "cp-001", "type": "bookmark"}, headers=headers)
    deep_read = reader.post("/api/events", json={"content_id": "cp-001", "type": "deep_read"}, headers=headers)
    assert click.status_code == 200
    assert bookmark.status_code == 200
    assert deep_read.status_code == 200
    north_star = deep_read.json()["north_star"]
    assert north_star["deep_read_closed_loop_events"] >= 2
    assert north_star["reading_events_total"] >= north_star["deep_read_closed_loop_events"]
    assert 0 < north_star["deep_read_closed_loop_rate"] <= 1
    assert "dau" not in north_star
    assert "reading_time" not in north_star


def test_alembic_migration_declares_only_l3_owned_tables() -> None:
    from pathlib import Path

    migration = Path(__file__).resolve().parents[1] / "db" / "alembic" / "versions" / "0001_l3_owned_tables.py"
    text = migration.read_text(encoding="utf-8")
    expected = {
        "users",
        "subscriptions",
        "user_interests",
        "user_follows",
        "reading_events",
        "briefs",
        "bookmarks",
        "api_keys",
        "api_usage_daily",
        "companion_usage",
    }
    for table in expected:
        assert f'"{table}"' in text
    assert "content_vertical_scores" not in text
    assert "content_translations" not in text


def test_alembic_env_uses_database_url_runtime_switch() -> None:
    from pathlib import Path

    env = Path(__file__).resolve().parents[1] / "db" / "alembic" / "env.py"
    text = env.read_text(encoding="utf-8")
    assert 'os.getenv("DATABASE_URL")' in text
    assert 'config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])' in text


def test_alembic_migration_upgrade_downgrade_round_trip() -> None:
    module = load_script_module("l3_migration_smoke")

    report = module.run_migration_smoke()
    assert report["status"] == "ok"
    assert set(report["created_tables"]) == module.EXPECTED_TABLES


def test_brief_jobs_persist_and_mock_email_delivery() -> None:
    public_brief = asyncio.run(generate_public_brief_job({}))
    assert public_brief["items"]

    before = len(mock_email_client.deliveries)
    personal = asyncio.run(generate_personal_brief_job({}, user_id=42, email="pro@example.com"))
    assert personal["user_id"] == 42
    assert personal["delivery"]["status"] == "sent"
    assert len(mock_email_client.deliveries) == before + 1
    assert get_repository().list_briefs()


def test_sqlalchemy_repository_covers_l3_owned_state() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(UserModel(id=99, email="sql@example.com", plan="free", locale="en"))
    session.commit()

    repo = SqlAlchemyL3Repository(session)
    repo.save_interests(99, ["ai", "backend", "python", "postgres", "agents"])
    assert repo.get_interests(99)["postgres"] == 1

    follows = repo.add_follow(99, "source", "CodePick Research")
    assert follows == [{"target_type": "source", "target_id": "CodePick Research"}]

    bookmark = repo.add_bookmark(99, "cp-001", "read again", ["queue"])
    assert bookmark["highlights"] == ["queue"]
    assert repo.list_bookmarks(99)[0]["content_id"] == "cp-001"

    repo.save_reading_event(99, "cp-001", "click")
    repo.save_reading_event(99, "cp-001", "deep_read")
    north_star = repo.north_star()
    assert north_star["deep_read_closed_loop_events"] == 1
    assert north_star["reading_events_total"] == 2
    assert north_star["deep_read_closed_loop_rate"] == 0.5

    assert repo.increment_companion_usage(99, date.today()) == 1
    assert repo.increment_companion_usage(99, date.today()) == 2

    repo.set_subscription_plan(99, "pro")
    assert repo.get_subscription_plan(99) == "pro"

    brief = generate_public_brief(StubContentReadProvider())
    repo.save_brief(brief)
    assert repo.list_briefs()[0].items


def test_sqlalchemy_repository_factory_commits_across_fresh_sessions(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    session.add(UserModel(id=101, email="factory@example.com", plan="free", locale="en"))
    session.commit()
    session.close()

    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "sqlalchemy")
    monkeypatch.setattr("codepick_l3.db.get_sessionmaker", lambda: Session)

    get_repository().save_interests(101, ["ai", "backend", "python", "postgres", "agents"])
    assert get_repository().get_interests(101)["agents"] == 1

    get_repository().add_bookmark(101, "cp-001", "persist", ["quote"])
    assert get_repository().list_bookmarks(101)[0]["note"] == "persist"

    get_repository().save_reading_event(101, "cp-001", "deep_read")
    north_star = get_repository().north_star()
    assert north_star["deep_read_closed_loop_events"] == 1
    assert north_star["reading_events_total"] == 1
    assert north_star["deep_read_closed_loop_rate"] == 1.0

    get_repository().set_subscription_plan(101, "pro")
    assert get_repository().get_subscription_plan(101) == "pro"

    assert get_repository().increment_companion_usage(101, date.today()) == 1
    assert get_repository().increment_companion_usage(101, date.today()) == 2
    monkeypatch.delenv("L3_REPOSITORY_BACKEND", raising=False)


def test_sqlalchemy_repository_factory_closes_owned_sessions(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    closed_sessions: list[int] = []

    class TrackingSession(Session):
        def close(self) -> None:
            closed_sessions.append(id(self))
            super().close()

    SessionFactory = sessionmaker(bind=engine, class_=TrackingSession, expire_on_commit=False)
    session = SessionFactory()
    session.add(UserModel(id=104, email="close@example.com", plan="free", locale="en"))
    session.commit()
    session.close()
    closed_sessions.clear()

    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "sqlalchemy")
    monkeypatch.setattr("codepick_l3.db.get_sessionmaker", lambda: SessionFactory)

    get_repository().save_interests(104, ["ai", "backend", "python", "postgres", "agents"])
    get_repository().get_interests(104)
    assert len(closed_sessions) == 2
    monkeypatch.delenv("L3_REPOSITORY_BACKEND", raising=False)


def test_sqlalchemy_login_creates_stable_distinct_users(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "sqlalchemy")
    monkeypatch.setattr("codepick_l3.db.get_sessionmaker", lambda: Session)

    first = reader.post("/api/auth/login", json={"email": "sql-a@example.com", "locale": "en"})
    second = reader.post("/api/auth/login", json={"email": "sql-b@example.com", "locale": "zh"})
    repeated = reader.post("/api/auth/login", json={"email": "SQL-A@example.com", "locale": "zh"})
    assert first.status_code == second.status_code == repeated.status_code == 200
    assert first.json()["user"]["id"] != second.json()["user"]["id"]
    assert repeated.json()["user"]["id"] == first.json()["user"]["id"]

    persisted = Session()
    try:
        users = persisted.query(UserModel).order_by(UserModel.id).all()
        assert [(user.email, user.locale) for user in users] == [
            ("sql-a@example.com", "zh"),
            ("sql-b@example.com", "zh"),
        ]
    finally:
        persisted.close()
    monkeypatch.delenv("L3_REPOSITORY_BACKEND", raising=False)


def test_reader_api_routes_persist_with_sqlalchemy_repository(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    session.add(UserModel(id=1, email="dev@example.com", plan="free", locale="en"))
    session.commit()
    session.close()

    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "sqlalchemy")
    monkeypatch.setattr("codepick_l3.db.get_sessionmaker", lambda: Session)

    get_repository().set_subscription_plan(1, "pro")
    login = reader.post("/api/auth/login", json={"email": "dev@example.com", "locale": "en"})
    assert login.status_code == 200
    assert login.json()["user"]["plan"] == "pro"
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    interests = reader.post("/api/interests", json={"tags": ["ai", "backend", "python", "postgres", "agents"]}, headers=headers)
    assert interests.status_code == 200
    assert reader.get("/api/interests", headers=headers).json()["tags"]["postgres"] == 1

    bookmark = reader.post("/api/bookmarks", json={"content_id": "cp-001", "note": "persisted via api", "highlights": ["queue"]}, headers=headers)
    assert bookmark.status_code == 200
    assert reader.get("/api/bookmarks", headers=headers).json()["items"][0]["note"] == "persisted via api"

    event = reader.post("/api/events", json={"content_id": "cp-001", "type": "deep_read"}, headers=headers)
    assert event.status_code == 200
    north_star = event.json()["north_star"]
    assert north_star["deep_read_closed_loop_events"] == 2
    assert north_star["reading_events_total"] == 2
    assert north_star["deep_read_closed_loop_rate"] == 1.0

    companion = reader.post("/api/companion", json={"content_id": "cp-001", "question": "why?"}, headers=headers)
    assert companion.status_code == 200
    assert companion.headers["content-type"].startswith("text/event-stream")

    persisted = Session()
    try:
        assert persisted.query(UserModel).filter_by(id=1).one().email == "dev@example.com"
        assert persisted.get(UserInterestModel, {"user_id": 1, "tag_code": "postgres"}).weight == 1
        assert persisted.get(BookmarkModel, {"user_id": 1, "content_id": "cp-001"}).note == "persisted via api"
        assert persisted.query(ReadingEventModel).filter_by(user_id=1, type="bookmark").count() == 1
        assert persisted.query(ReadingEventModel).filter_by(user_id=1, type="deep_read").count() == 1
        assert persisted.get(CompanionUsageModel, {"user_id": 1, "day": date.today()}).count == 1
    finally:
        persisted.close()
    monkeypatch.delenv("L3_REPOSITORY_BACKEND", raising=False)


def test_sqlalchemy_quota_store_persists_api_key_usage(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    session.add(UserModel(id=100, email="api@example.com", plan="free", locale="en"))
    session.add(
        ApiKeyModel(
            id=1,
            owner_user_id=100,
            key_hash=hash_key("persisted_key"),
            prefix="persisted",
            scopes=["read"],
            rate_limit_rpm=20,
            daily_quota=1,
            status="active",
        )
    )
    session.commit()
    session.close()

    monkeypatch.setenv("L3_QUOTA_BACKEND", "sqlalchemy")
    monkeypatch.setattr("codepick_l3.db.get_sessionmaker", lambda: Session)
    record = require_api_key("persisted_key")
    assert record.owner_user_id == 100

    usage_session = Session()
    usage = usage_session.get(ApiUsageDailyModel, {"key_id": 1, "day": date.today()})
    assert usage is not None
    assert usage.count == 1
    usage_session.close()

    response = public.get("/v1/today", headers={"X-API-Key": "persisted_key"})
    assert response.status_code == 429
    detail = response.json()["detail"]
    assert detail["error"] == "daily_quota_exceeded"
    assert detail["reset_seconds"] == 86400
    monkeypatch.delenv("L3_QUOTA_BACKEND", raising=False)


def test_sqlalchemy_quota_store_enforces_rpm(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    session.add(UserModel(id=102, email="rpm@example.com", plan="free", locale="en"))
    session.add(
        ApiKeyModel(
            id=2,
            owner_user_id=102,
            key_hash=hash_key("sql_rpm_key"),
            prefix="sql_rpm",
            scopes=["read"],
            rate_limit_rpm=1,
            daily_quota=20,
            status="active",
        )
    )
    session.commit()
    session.close()

    rate_window.minute.pop(hash_key("sql_rpm_key"), None)
    monkeypatch.setenv("L3_QUOTA_BACKEND", "sqlalchemy")
    monkeypatch.setattr("codepick_l3.db.get_sessionmaker", lambda: Session)
    monkeypatch.setattr("codepick_l3.usage.time.time", lambda: 240.0)
    assert public.get("/v1/today", headers={"X-API-Key": "sql_rpm_key"}).status_code == 200
    response = public.get("/v1/today", headers={"X-API-Key": "sql_rpm_key"})
    assert response.status_code == 429
    detail = response.json()["detail"]
    assert detail["error"] == "rate_limit_exceeded"
    assert 1 <= detail["reset_seconds"] <= 60
    monkeypatch.delenv("L3_QUOTA_BACKEND", raising=False)


def test_sqlalchemy_api_key_lifecycle_and_scope_enforcement(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    session.add(UserModel(id=103, email="lifecycle@example.com", plan="free", locale="en"))
    session.commit()
    session.close()

    monkeypatch.setenv("L3_QUOTA_BACKEND", "sqlalchemy")
    monkeypatch.setattr("codepick_l3.db.get_sessionmaker", lambda: Session)
    from codepick_l3.usage import create_api_key, list_api_keys, revoke_api_key

    created = create_api_key(103, scopes=["read"])
    raw_key = created["key"]
    assert public.get("/v1/today", headers={"X-API-Key": raw_key}).status_code == 200
    listed = list_api_keys(103)
    assert any(item["prefix"] == created["prefix"] and "key" not in item for item in listed)
    assert revoke_api_key(103, created["prefix"]) is True
    assert public.get("/v1/today", headers={"X-API-Key": raw_key}).status_code == 401

    write_only = create_api_key(103, scopes=["write"])
    response = public.get("/v1/today", headers={"X-API-Key": write_only["key"]})
    assert response.status_code == 403
    assert response.json()["detail"] == "read scope required"
    monkeypatch.delenv("L3_QUOTA_BACKEND", raising=False)


def test_sqlalchemy_quota_api_key_operations_close_sessions(monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    closed_sessions: list[int] = []

    class TrackingSession(Session):
        def close(self) -> None:
            closed_sessions.append(id(self))
            super().close()

    SessionFactory = sessionmaker(bind=engine, class_=TrackingSession, expire_on_commit=False)
    session = SessionFactory()
    session.add(UserModel(id=105, email="quota-close@example.com", plan="free", locale="en"))
    session.commit()
    session.close()
    closed_sessions.clear()

    monkeypatch.setenv("L3_QUOTA_BACKEND", "sqlalchemy")
    monkeypatch.setattr("codepick_l3.db.get_sessionmaker", lambda: SessionFactory)
    from codepick_l3.usage import create_api_key, list_api_keys, revoke_api_key

    created = create_api_key(105, scopes=["read"])
    list_api_keys(105)
    require_api_key(created["key"])
    revoke_api_key(105, created["prefix"])
    assert len(closed_sessions) == 4
    monkeypatch.delenv("L3_QUOTA_BACKEND", raising=False)


def test_runtime_switch_defaults_to_stub_mock_and_sandbox(monkeypatch) -> None:
    monkeypatch.delenv("L3_USE_STUB_L2", raising=False)
    monkeypatch.delenv("EMAIL_PROVIDER", raising=False)
    monkeypatch.delenv("BILLING_ENVIRONMENT", raising=False)
    reset_settings_cache()
    assert isinstance(get_content_provider(), StubContentReadProvider)
    assert get_email_client() is mock_email_client
    assert "sandbox-payments" in get_billing_client().checkout_url(1, "month")


def test_l2_provider_switch_requires_base_url(monkeypatch) -> None:
    monkeypatch.setenv("L3_USE_STUB_L2", "false")
    monkeypatch.delenv("L2_BASE_URL", raising=False)
    reset_settings_cache()
    try:
        get_content_provider()
        raise AssertionError("expected ProviderUnavailable")
    except ProviderUnavailable as exc:
        assert "L2_BASE_URL" in str(exc)
    finally:
        monkeypatch.setenv("L3_USE_STUB_L2", "true")
        reset_settings_cache()


def test_l2_provider_switch_builds_http_provider(monkeypatch) -> None:
    monkeypatch.setenv("L3_USE_STUB_L2", "false")
    monkeypatch.setenv("L2_BASE_URL", "https://l2.example.test")
    monkeypatch.setenv("L2_API_KEY", "l2-key")
    reset_settings_cache()
    provider = get_content_provider()
    assert isinstance(provider, L2HttpContentReadProvider)
    assert provider.base_url == "https://l2.example.test"
    monkeypatch.setenv("L3_USE_STUB_L2", "true")
    reset_settings_cache()


def test_l2_http_provider_contract_requests_and_responses() -> None:
    fixture = StubContentReadProvider().get("cp-001").model_dump(mode="json")
    seen: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            seen.append({"path": parsed.path, "query": query, "authorization": self.headers.get("Authorization")})
            if parsed.path == "/content":
                body = {"items": [fixture], "next_cursor": None, "total": 1}
            elif parsed.path == "/content/cp-001":
                body = fixture
            elif parsed.path == "/recommend":
                body = {"items": [fixture]}
            elif parsed.path == "/companion":
                body = {"chunks": ["first", "second"]}
            else:
                self.send_response(404)
                self.end_headers()
                return
            payload = json.dumps(body, default=str).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        provider = L2HttpContentReadProvider(base_url, api_key="l2-key", timeout=2)
        page = provider.list(vertical="ai", cursor="0", limit=1, filters={"sort": "score"})
        assert page.total == 1
        assert page.items[0].id == "cp-001"
        detail = provider.get("cp-001")
        assert detail.translations["zh"].title
        recommendations = provider.recommend(7, vertical="ai", limit=1)
        assert recommendations[0].id == "cp-001"
        assert list(provider.companion("cp-001", "why?")) == ["first", "second"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert {entry["path"] for entry in seen} == {"/content", "/content/cp-001", "/recommend", "/companion"}
    assert all(entry["authorization"] == "Bearer l2-key" for entry in seen)
    list_call = next(entry for entry in seen if entry["path"] == "/content")
    assert list_call["query"]["vertical"] == ["ai"]
    assert list_call["query"]["status"] == ["COMPLETED"]
    assert list_call["query"]["sort"] == ["score"]


def test_l2_http_provider_maps_transport_errors_to_provider_unavailable() -> None:
    provider = L2HttpContentReadProvider("http://127.0.0.1:1", timeout=0.1)
    try:
        provider.list()
        raise AssertionError("expected ProviderUnavailable")
    except ProviderUnavailable as exc:
        assert "L2 provider request failed" in str(exc)


def test_email_and_billing_runtime_switches(monkeypatch) -> None:
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "resend-key")
    monkeypatch.setenv("BILLING_ENVIRONMENT", "production")
    monkeypatch.setenv("PADDLE_CHECKOUT_BASE_URL", "https://checkout.paddle.example")
    reset_settings_cache()
    assert isinstance(get_email_client(), ConfiguredEmailClient)
    billing = get_billing_client()
    assert isinstance(billing, PaddleBilling)
    assert "provider=paddle" in billing.checkout_url(1, "year")
    assert "user_id=1" in billing.checkout_url(1, "earlybird")
    monkeypatch.setenv("EMAIL_PROVIDER", "mock")
    monkeypatch.setenv("BILLING_ENVIRONMENT", "sandbox")
    reset_settings_cache()


def test_parse_billing_webhook_accepts_flat_and_nested_contracts() -> None:
    assert parse_billing_webhook({"user_id": 10, "event": "subscription.activated"}) == {"user_id": 10, "event": "subscription.activated", "plan": "pro"}
    assert parse_billing_webhook({"event_type": "subscription.paused", "data": {"custom_data": {"user_id": "10"}}}) == {"user_id": 10, "event": "subscription.paused", "plan": "free"}


def test_resend_email_client_posts_brief_payload_to_configured_endpoint() -> None:
    brief = generate_public_brief(StubContentReadProvider())
    seen: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            seen.append({"path": self.path, "authorization": self.headers.get("Authorization"), "body": body})
            payload = json.dumps({"id": "resend-msg-1"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = ConfiguredEmailClient(
            "resend",
            api_key="resend-key",
            sender="CodePick <briefs@example.test>",
            resend_api_url=f"http://127.0.0.1:{server.server_port}/emails",
        )
        delivery = client.send_brief("reader@example.test", brief)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert delivery.status == "queued"
    assert delivery.metadata["provider_message_id"] == "resend-msg-1"
    assert seen[0]["path"] == "/emails"
    assert seen[0]["authorization"] == "Bearer resend-key"
    assert seen[0]["body"]["to"] == ["reader@example.test"]
    assert seen[0]["body"]["from"] == "CodePick <briefs@example.test>"
    assert brief.items[0].title in seen[0]["body"]["text"]


def test_resend_email_client_maps_transport_failure() -> None:
    brief = generate_public_brief(StubContentReadProvider())
    client = ConfiguredEmailClient("resend", api_key="resend-key", resend_api_url="http://127.0.0.1:1/emails")
    try:
        client.send_brief("reader@example.test", brief)
        raise AssertionError("expected EmailDeliveryError")
    except EmailDeliveryError as exc:
        assert "Resend email delivery failed" in str(exc)


def test_ses_email_client_uses_boto3_send_email(monkeypatch) -> None:
    brief = generate_public_brief(StubContentReadProvider())
    calls: list[dict] = []

    class SesClient:
        def send_email(self, **kwargs):
            calls.append(kwargs)
            return {"MessageId": "ses-msg-1"}

    module = types.SimpleNamespace(client=lambda service, region_name: SesClient())
    monkeypatch.setitem(sys.modules, "boto3", module)
    client = ConfiguredEmailClient("ses", region="us-east-1", sender="CodePick <briefs@example.test>")
    delivery = client.send_brief("reader@example.test", brief)
    assert delivery.metadata["provider_message_id"] == "ses-msg-1"
    assert calls[0]["Source"] == "CodePick <briefs@example.test>"
    assert calls[0]["Destination"]["ToAddresses"] == ["reader@example.test"]
    assert brief.items[0].title in calls[0]["Message"]["Body"]["Text"]["Data"]


def test_arq_worker_settings_and_redis_env(monkeypatch) -> None:
    monkeypatch.setenv("ARQ_REDIS_HOST", "redis.internal")
    monkeypatch.setenv("ARQ_REDIS_PORT", "6380")
    monkeypatch.setenv("ARQ_REDIS_DATABASE", "2")
    assert redis_settings() == {"host": "redis.internal", "port": 6380, "database": 2}
    function_names = {fn.__name__ for fn in WorkerSettings.functions}
    assert {"generate_public_brief_job", "generate_personal_brief_job"} <= function_names
    assert WorkerSettings.max_jobs >= 1
    assert WorkerSettings.cron_jobs


def test_brief_cron_uses_env_schedule(monkeypatch) -> None:
    monkeypatch.setenv("BRIEF_PUBLIC_CRON_HOUR_UTC", "6")
    monkeypatch.setenv("BRIEF_PUBLIC_CRON_MINUTE_UTC", "30")
    cron_job = brief_cron_jobs()[0]
    assert cron_job.name == "generate_public_brief_job"
    assert cron_job.hour == 6
    assert cron_job.minute == 30


def test_brief_worker_operations_are_documented_in_makefile() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    makefile = (root / "Makefile").read_text(encoding="utf-8")
    enqueue_script = (root / "scripts" / "enqueue_brief.py").read_text(encoding="utf-8")
    assert "brief-worker" in makefile
    assert "arq jobs.WorkerSettings" in makefile
    assert "brief-enqueue-public" in makefile
    assert "create_pool" in enqueue_script
    assert "generate_personal_brief_job" in enqueue_script


def test_mcp_tools_return_public_trimmed_contract() -> None:
    manifest = mcp_server.tool_manifest()
    assert {tool["name"] for tool in manifest["tools"]} == {"today", "search", "item"}
    today = mcp_server.today(limit=1)
    assert today["items"]
    assert all(set(result) == PUBLIC_CONTENT_FIELDS for result in today["items"])
    item = mcp_server.item(today["items"][0]["id"])
    assert set(item) == PUBLIC_CONTENT_FIELDS
    assert "base_analysis" not in item
    assert "translations" not in item
    assert "scores" in item
    search = mcp_server.search("Python")
    assert all(set(result) == PUBLIC_CONTENT_FIELDS for result in search["items"])
    assert all("base_analysis" not in result for result in search["items"])


def test_mcp_search_matches_public_summary_contract() -> None:
    public_response = public.get("/v1/search", params={"q": "MCP"}, headers={"X-API-Key": "cp_test_key"})
    assert public_response.status_code == 200
    mcp_response = mcp_server.search("MCP")
    assert {item["id"] for item in mcp_response["items"]} == {item["id"] for item in public_response.json()["items"]}


def test_mcp_tools_reject_out_of_range_limits() -> None:
    for action in [
        lambda: mcp_server.today(limit=0),
        lambda: mcp_server.today(limit=51),
        lambda: mcp_server.search("MCP", limit=0),
        lambda: mcp_server.search("MCP", limit=51),
    ]:
        with pytest.raises(ValueError, match="limit must be between 1 and 50"):
            action()


def test_mcp_smoke_runner_is_operationally_documented() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    makefile = (root / "Makefile").read_text(encoding="utf-8")
    runner = (root / "scripts" / "run_mcp_server.py").read_text(encoding="utf-8")
    assert "mcp-smoke" in makefile
    assert "scripts/run_mcp_server.py" in makefile
    assert "ensure_paths()" in runner
    assert mcp_server.smoke()["ok"] is True


def test_pricing_and_currency_invariants() -> None:
    from codepick_l3.config import get_settings

    settings = get_settings()
    assert settings.price_pro_month_usd == "8"
    assert settings.price_pro_year_usd == "79"
    assert settings.price_earlybird_usd == "4.9"
    checkout = get_billing_client().checkout_url(1, "month")
    assert "currency=USD" in checkout


def test_local_operations_files_capture_required_defaults() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    env_text = (root / ".env.example").read_text(encoding="utf-8")
    compose_text = (root / "docker-compose.yml").read_text(encoding="utf-8")
    makefile = (root / "Makefile").read_text(encoding="utf-8")

    assert "L3_USE_STUB_L2=true" in env_text
    assert "L3_AUTH_LOGIN_MODE=development" in env_text
    assert "BILLING_ENVIRONMENT=sandbox" in env_text
    assert "PRICE_PRO_MONTH_USD=8" in env_text
    assert "PRICE_PRO_YEAR_USD=79" in env_text
    assert "PRICE_EARLYBIRD_USD=4.9" in env_text
    assert "postgres:16" in compose_text
    assert "redis:7" in compose_text
    assert "5432:5432" in compose_text
    assert "6379:6379" in compose_text
    assert "pg_isready -U codepick -d codepick_l3" in compose_text
    assert '["CMD", "redis-cli", "ping"]' in compose_text
    assert "scripts/run_reader_api.py" in makefile
    assert "scripts/run_public_api.py" in makefile
    assert "l3-clean" in makefile
    assert "scripts/l3_clean.py" in makefile
    assert "infra-status" in makefile


def test_l3_clean_script_declares_generated_artifacts() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    text = (root / "scripts" / "l3_clean.py").read_text(encoding="utf-8")
    for marker in [".pytest_cache", "codepick_l3.egg-info", "tsconfig.tsbuildinfo", "test-results", "playwright-report", ".next", "__pycache__"]:
        assert marker in text


def test_local_api_launchers_bootstrap_python_paths() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    bootstrap = (root / "scripts" / "path_bootstrap.py").read_text(encoding="utf-8")
    reader_runner = (root / "scripts" / "run_reader_api.py").read_text(encoding="utf-8")
    public_runner = (root / "scripts" / "run_public_api.py").read_text(encoding="utf-8")
    smoke_runner = (root / "scripts" / "l3_smoke.py").read_text(encoding="utf-8")
    for marker in ['"services" / "shared"', '"services" / "reader-api"', '"services" / "public-api"', '"workers" / "briefs"', '"services" / "mcp-server"']:
        assert marker in bootstrap
    assert "ensure_paths()" in reader_runner
    assert "ensure_paths()" in public_runner
    assert "pythonpath_env()" in smoke_runner


def test_l3_preflight_dev_defaults_ready(monkeypatch) -> None:
    evaluate_preflight = load_script_module("l3_preflight").evaluate_preflight

    for key in ["L3_USE_STUB_L2", "L3_REPOSITORY_BACKEND", "L3_QUOTA_BACKEND", "EMAIL_PROVIDER", "BILLING_ENVIRONMENT", "ARQ_REDIS_HOST", "ARQ_REDIS_PORT"]:
        monkeypatch.delenv(key, raising=False)
    report = evaluate_preflight(final=False)
    assert report["status"] == "ready"
    assert report["mode"] == "dev"


def test_l3_preflight_final_blocks_dev_defaults(monkeypatch) -> None:
    evaluate_preflight = load_script_module("l3_preflight").evaluate_preflight

    monkeypatch.setenv("JWT_SECRET", "dev-secret")
    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", "dev-webhook-secret")
    monkeypatch.setenv("L3_USE_STUB_L2", "true")
    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "memory")
    monkeypatch.setenv("L3_QUOTA_BACKEND", "memory")
    monkeypatch.setenv("EMAIL_PROVIDER", "mock")
    monkeypatch.setenv("BILLING_ENVIRONMENT", "sandbox")
    report = evaluate_preflight(final=True)
    assert report["status"] == "blocked"
    blocked = {check["name"] for check in report["checks"] if not check["ready"]}
    assert {"jwt_secret", "content_provider", "repository", "quota", "billing", "email"} <= blocked


def test_l3_preflight_final_accepts_explicit_integration_config(monkeypatch) -> None:
    evaluate_preflight = load_script_module("l3_preflight").evaluate_preflight

    monkeypatch.setenv("JWT_SECRET", "prod-jwt-secret")
    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", "prod-webhook-secret")
    monkeypatch.setenv("L3_USE_STUB_L2", "false")
    monkeypatch.setenv("L2_BASE_URL", "https://l2.example.test")
    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "sqlalchemy")
    monkeypatch.setenv("L3_QUOTA_BACKEND", "sqlalchemy")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://codepick:secret@db/codepick_l3")
    monkeypatch.setenv("BILLING_ENVIRONMENT", "production")
    monkeypatch.setenv("PADDLE_CHECKOUT_BASE_URL", "https://checkout.paddle.com")
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "resend-key")
    monkeypatch.setenv("EMAIL_FROM", "CodePick <briefs@example.test>")
    monkeypatch.setenv("L3_AUTH_LOGIN_MODE", "external")
    monkeypatch.setenv("ARQ_REDIS_HOST", "redis")
    monkeypatch.setenv("ARQ_REDIS_PORT", "6379")
    report = evaluate_preflight(final=True)
    assert report["status"] == "ready"


def test_l3_preflight_final_requires_https_l2_url(monkeypatch) -> None:
    evaluate_preflight = load_script_module("l3_preflight").evaluate_preflight

    monkeypatch.setenv("JWT_SECRET", "prod-jwt-secret")
    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", "prod-webhook-secret")
    monkeypatch.setenv("L3_USE_STUB_L2", "false")
    monkeypatch.setenv("L2_BASE_URL", "http://l2.example.test")
    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "sqlalchemy")
    monkeypatch.setenv("L3_QUOTA_BACKEND", "sqlalchemy")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://codepick:secret@db/codepick_l3")
    monkeypatch.setenv("BILLING_ENVIRONMENT", "production")
    monkeypatch.setenv("PADDLE_CHECKOUT_BASE_URL", "https://checkout.paddle.com")
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "resend-key")
    monkeypatch.setenv("EMAIL_FROM", "CodePick <briefs@example.test>")
    monkeypatch.setenv("ARQ_REDIS_HOST", "redis")
    monkeypatch.setenv("ARQ_REDIS_PORT", "6379")

    report = evaluate_preflight(final=True)
    assert report["status"] == "blocked"
    content_provider = next(check for check in report["checks"] if check["name"] == "content_provider")
    assert content_provider["ready"] is False
    assert "HTTPS L2_BASE_URL" in content_provider["detail"]


def test_l3_preflight_final_requires_https_paddle_checkout_url(monkeypatch) -> None:
    evaluate_preflight = load_script_module("l3_preflight").evaluate_preflight

    monkeypatch.setenv("JWT_SECRET", "prod-jwt-secret")
    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", "prod-webhook-secret")
    monkeypatch.setenv("L3_USE_STUB_L2", "false")
    monkeypatch.setenv("L2_BASE_URL", "https://l2.example.test")
    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "sqlalchemy")
    monkeypatch.setenv("L3_QUOTA_BACKEND", "sqlalchemy")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://codepick:secret@db/codepick_l3")
    monkeypatch.setenv("BILLING_ENVIRONMENT", "production")
    monkeypatch.setenv("PADDLE_CHECKOUT_BASE_URL", "http://checkout.paddle.com")
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "resend-key")
    monkeypatch.setenv("EMAIL_FROM", "CodePick <briefs@example.test>")
    monkeypatch.setenv("ARQ_REDIS_HOST", "redis")
    monkeypatch.setenv("ARQ_REDIS_PORT", "6379")

    report = evaluate_preflight(final=True)
    assert report["status"] == "blocked"
    billing = next(check for check in report["checks"] if check["name"] == "billing")
    assert billing["ready"] is False
    assert "HTTPS production Paddle URL" in billing["detail"]


def test_l3_preflight_final_requires_postgresql_database_url(monkeypatch) -> None:
    evaluate_preflight = load_script_module("l3_preflight").evaluate_preflight

    monkeypatch.setenv("JWT_SECRET", "prod-jwt-secret")
    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", "prod-webhook-secret")
    monkeypatch.setenv("L3_USE_STUB_L2", "false")
    monkeypatch.setenv("L2_BASE_URL", "https://l2.example.test")
    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "sqlalchemy")
    monkeypatch.setenv("L3_QUOTA_BACKEND", "sqlalchemy")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///not-final.db")
    monkeypatch.setenv("BILLING_ENVIRONMENT", "production")
    monkeypatch.setenv("PADDLE_CHECKOUT_BASE_URL", "https://checkout.paddle.com")
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "resend-key")
    monkeypatch.setenv("EMAIL_FROM", "CodePick <briefs@example.test>")
    monkeypatch.setenv("ARQ_REDIS_HOST", "redis")
    monkeypatch.setenv("ARQ_REDIS_PORT", "6379")

    report = evaluate_preflight(final=True)
    assert report["status"] == "blocked"
    blocked = {check["name"] for check in report["checks"] if not check["ready"]}
    assert {"repository", "quota"} <= blocked
    for check in report["checks"]:
        if check["name"] in {"repository", "quota"}:
            assert "PostgreSQL DATABASE_URL" in check["detail"]


def test_l3_preflight_final_requires_explicit_redis(monkeypatch) -> None:
    evaluate_preflight = load_script_module("l3_preflight").evaluate_preflight

    monkeypatch.setenv("JWT_SECRET", "prod-jwt-secret")
    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", "prod-webhook-secret")
    monkeypatch.setenv("L3_USE_STUB_L2", "false")
    monkeypatch.setenv("L2_BASE_URL", "https://l2.example.test")
    monkeypatch.setenv("L3_REPOSITORY_BACKEND", "sqlalchemy")
    monkeypatch.setenv("L3_QUOTA_BACKEND", "sqlalchemy")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://codepick:secret@db/codepick_l3")
    monkeypatch.setenv("BILLING_ENVIRONMENT", "production")
    monkeypatch.setenv("PADDLE_CHECKOUT_BASE_URL", "https://checkout.paddle.com")
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "resend-key")
    monkeypatch.setenv("EMAIL_FROM", "CodePick <briefs@example.test>")
    monkeypatch.delenv("ARQ_REDIS_HOST", raising=False)
    monkeypatch.delenv("ARQ_REDIS_PORT", raising=False)

    report = evaluate_preflight(final=True)
    assert report["status"] == "blocked"
    redis = next(check for check in report["checks"] if check["name"] == "redis")
    assert redis["ready"] is False
    assert "explicit ARQ_REDIS_HOST and ARQ_REDIS_PORT" in redis["detail"]


def test_l3_final_probe_declares_live_final_integration_checks() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts" / "l3_final_probe.py").read_text(encoding="utf-8")
    makefile = (root / "Makefile").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    checklist = (root / "docs" / "L3-final-integration-checklist.md").read_text(encoding="utf-8")

    for marker in [
        "evaluate_preflight(final=True)",
        "get_content_provider()",
        "status=\"COMPLETED\"",
        "DATABASE_URL",
        "Base.metadata.tables.keys()",
        "api_usage_daily",
        "ARQ_REDIS_HOST",
        "taxonomy_categories",
        "audiences",
        "audience_categories",
        "create_pool",
        "--send-test-email",
        "--enqueue-brief",
        "get_email_client()",
        "Paddle",
    ]:
        assert marker in script
    assert "l3-final-probe:" in makefile
    assert "python scripts/l3_final_probe.py" in makefile
    assert "make l3-final-probe" in readme
    assert "python scripts/l3_final_probe.py" in checklist
    assert "--send-test-email ops@example.com --enqueue-brief" in checklist


def test_readme_uses_real_l3_spec_artifact_names() -> None:
    from pathlib import Path

    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    expected = [
        "L3-\u5e94\u7528\u4e0e\u5206\u53d1-\u4ea7\u54c1\u6587\u6863.html",
        "L3-\u5e94\u7528\u4e0e\u5206\u53d1-\u67b6\u6784\u8bbe\u8ba1.html",
        "L3-\u5f00\u53d1Plan-\u8be6\u5c3d\u7248.html",
        "L3-\u5b9e\u65bd\u624b\u518c-\u4ea4\u4ed8\u5305.html",
    ]
    for filename in expected:
        assert filename in readme
    for fragment in ["\u6434", "\u5bee", "\u7039", "\u93bc", "\u95b8", "\u95ba", "\u940e", "\u5a34", "\ufffd"]:
        assert fragment not in readme

def test_ci_runs_l3_cleanup_after_gates() -> None:
    from pathlib import Path

    workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "l3-ci.yml").read_text(encoding="utf-8")
    assert "python scripts/l3_clean.py" in workflow
    assert "python ../../scripts/l3_clean.py" in workflow


def test_ci_runs_backend_release_gates() -> None:
    from pathlib import Path

    workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "l3-ci.yml").read_text(encoding="utf-8")
    assert "python scripts/l3_preflight.py" in workflow
    assert "python scripts/l3_migration_smoke.py" in workflow
    assert "python scripts/l3_smoke.py" in workflow


def test_ci_runs_reader_web_production_build() -> None:
    from pathlib import Path

    workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "l3-ci.yml").read_text(encoding="utf-8")
    assert "npm run typecheck" in workflow
    assert "npm run build" in workflow
    assert "npm run test:e2e" in workflow


def test_makefile_exposes_full_l3_verify_handoff_gate() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    makefile = (root / "Makefile").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    verify_script = (root / "scripts" / "l3_verify.py").read_text(encoding="utf-8")
    assert "l3-verify:" in makefile
    assert "python scripts/l3_verify.py" in makefile
    assert "try:" in verify_script
    assert "finally:" in verify_script
    for marker in [
        "l3_preflight.py",
        "l3_migration_smoke.py",
        "l3_smoke.py",
        "shutil.which(\"npm\")",
        'npm_args("--prefix", str(READER_WEB), "run", "typecheck")',
        'npm_args("--prefix", str(READER_WEB), "run", "build")',
        "node_modules",
        "playwright.cmd",
        "PLAYWRIGHT_EXTERNAL_SERVER",
        "wait_for_reader_web",
        "stop_process_tree",
        "run_reader_web_e2e",
        "l3_clean.py",
    ]:
        assert marker in verify_script
    assert "L3 VERIFY: PASS" in verify_script
    assert "python scripts/l3_verify.py" in readme
    assert "make l3-verify" in readme
    assert "cross-platform full handoff gate" in readme


def test_readme_documents_public_api_quota_envelope_and_ready_header() -> None:
    from pathlib import Path

    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    for marker in [
        'curl -H "X-API-Key: cp_test_key" http://127.0.0.1:8001/v1/ready',
        '"quota": { "daily": 200, "rate_limit_rpm": 20 }',
        'GET /v1/items/{id}` uses `{ "item": { ...public fields... }, "quota": { ... } }`',
        "/v1/ready` authenticates with `X-API-Key` but does not consume daily quota or RPM",
    ]:
        assert marker in readme


def test_required_l3_html_spec_artifacts_are_present() -> None:
    from pathlib import Path

    docs = Path(__file__).resolve().parents[1] / "docs"
    required_specs = {
        "L3-\u5e94\u7528\u4e0e\u5206\u53d1-\u4ea7\u54c1\u6587\u6863.html": ["Free", "Pro", "$8/month", "$79/year", "$4.9", "\u6df1\u5ea6\u9605\u8bfb\u95ed\u73af\u7387", "ContentReadProvider"],
        "L3-\u5e94\u7528\u4e0e\u5206\u53d1-\u67b6\u6784\u8bbe\u8ba1.html": ["/api", "/v1", "JWT", "X-API-Key", "require_plan", "users", "api_usage_daily"],
        "L3-\u5f00\u53d1Plan-\u8be6\u5c3d\u7248.html": ["E0", "E9"],
        "L3-\u5b9e\u65bd\u624b\u518c-\u4ea4\u4ed8\u5305.html": ["L3", "Codex"],
    }

    for filename, markers in required_specs.items():
        path = docs / filename
        assert path.exists(), f"missing required L3 spec artifact: {filename}"
        text = path.read_text(encoding="utf-8")
        assert "<html" in text.lower()
        for marker in markers:
            assert marker in text, f"{filename} missing marker {marker}"


def test_final_integration_checklist_covers_release_readiness() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    checklist = (root / "docs" / "L3-final-integration-checklist.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    required = [
        "python scripts/l3_verify.py",
        "L3 VERIFY: PASS",
        "python scripts/l3_preflight.py --final",
        "status=ready",
        "L3_MIGRATION_SMOKE_DATABASE_URL",
        "L3_USE_STUB_L2=false",
        "L2_BASE_URL",
        "HTTPS L2_BASE_URL",
        "L3_REPOSITORY_BACKEND=sqlalchemy",
        "L3_QUOTA_BACKEND=sqlalchemy",
        "DATABASE_URL",
        "ARQ_REDIS_HOST",
        "EMAIL_PROVIDER=resend",
        "EMAIL_PROVIDER=ses",
        "BILLING_ENVIRONMENT=production",
        "PADDLE_CHECKOUT_BASE_URL",
        "HTTPS production Paddle checkout",
        "PADDLE_WEBHOOK_SECRET",
        "JWT_SECRET",
        "$8/month",
        "$79/year",
        "$4.9",
        "Go/No-Go",
        "Rollback",
        "Post-Release Checks",
        "/api",
        "/v1",
        "require_plan",
        "deep_read_closed_loop_rate",
    ]
    for marker in required:
        assert marker in checklist
    assert "L3-final-integration-checklist.md" in readme


def test_sprint_handoff_records_feature_self_test_coverage_and_residuals() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    handoff = (root / "docs" / "L3-sprint-handoff.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")

    for marker in [
        "S1 Foundation And Display",
        "S2 Account And Personalization",
        "S3 Companion And Brief",
        "S4 Commercialization",
        "S5 API, MCP, I18n, And SEO",
        "Implemented features",
        "Self-test evidence",
        "Coverage/evidence",
        "Remaining work",
        "L3 VERIFY: PASS",
        "108 passed",
        "26 passed",
        "Final Integration Residuals",
        "real HTTPS L2",
        "Paddle production",
    ]:
        assert marker in handoff
    assert "L3-sprint-handoff.md" in readme


def test_completion_audit_maps_l3_requirements_to_evidence() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    audit = (root / "docs" / "L3-completion-audit.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")

    for marker in [
        "Independent L3 application and distribution layer: current local gates are green, including the full `l3_verify.py` wrapper.",
        "Final integration with real L2, PostgreSQL, Redis/Arq, Resend/SES, and Paddle: prepared and gated",
        "E0 engineering baseline",
        "E1 content input through `ContentReadProvider`",
        "E2 public picks",
        "E3 account/JWT",
        "E4 interests",
        "E5 AI companion",
        "E6 public/personal brief generation",
        "E7 USD commercial flow",
        "E8 Public API and MCP",
        "E9 i18n and SEO",
        "`/api` and `/v1` trust boundary separation",
        "L3-owned tables only",
        "python scripts/l3_final_probe.py --send-test-email ops@example.com --enqueue-brief",
            "108 passed",
        "26 passed",
        "python scripts/l3_verify.py",
    ]:
        assert marker in audit
    assert "L3-completion-audit.md" in readme

def test_reader_web_source_has_expected_utf8_copy() -> None:
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    files = [
        root / "apps" / "reader-web" / "components" / "Header.tsx",
        root / "apps" / "reader-web" / "components" / "LoginForm.tsx",
        root / "apps" / "reader-web" / "components" / "BillingPanel.tsx",
        root / "apps" / "reader-web" / "components" / "CompanionWidget.tsx",
        root / "apps" / "reader-web" / "components" / "BriefGate.tsx",
        root / "apps" / "reader-web" / "components" / "ApiKeyPanel.tsx",
        root / "apps" / "reader-web" / "lib" / "api.ts",
        root / "apps" / "reader-web" / "app" / "[locale]" / "page.tsx",
        root / "apps" / "reader-web" / "app" / "[locale]" / "items" / "[id]" / "page.tsx",
        root / "apps" / "reader-web" / "app" / "[locale]" / "brief" / "page.tsx",
        root / "apps" / "reader-web" / "tests" / "reader.spec.ts",
    ]
    expected = {
        "\u4e2d\u6587",
        "\u65e9\u62a5",
        "\u516c\u5171\u7cbe\u9009",
        "\u9762\u5411\u5de5\u7a0b\u9605\u8bfb\u7684\u9ad8\u4fe1\u53f7 COMPLETED \u5185\u5bb9\u3002",
        "\u5f02\u6b65 Python \u667a\u80fd\u4f53\u7684\u8fd0\u884c\u6210\u672c\u6b63\u5728\u4e0b\u964d",
        "\u516d\u7ef4\u8bc4\u5206",
        "AI \u4f34\u8bfb",
        "\u6c99\u7bb1\u7ed3\u8d26\uff1a",
        "Public API \u5bc6\u94a5",
    }
    bad_fragments = [
        "\u6d93",
        "\u934f",
        "\u93c3",
        "\u9427",
        "\u7025",
        "\u95ab",
        "\u5bb8",
        "\u9396",
        "\u7459",
        "\u7490",
        "\u5a23",
        "\u7eee",
        "\u6dc7",
        "\ufffd",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
    semantic_text = re.sub(r"\\u([0-9a-fA-F]{4})", lambda match: chr(int(match.group(1), 16)), combined)
    for marker in expected:
        assert marker in semantic_text
    for fragment in bad_fragments:
        assert fragment not in combined


def test_stub_l2_fixture_has_expected_utf8_translations() -> None:
    detail = StubContentReadProvider().get("cp-001")
    translation = detail.translations["zh"]
    semantic_text = "\n".join(
        [
            translation.title,
            translation.summary,
            translation.base_analysis["summary"],
            "\n".join(translation.base_analysis["viewpoints"]),
            "\n".join(translation.base_analysis["quotes"]),
        ]
    )
    for marker in [
        "\u5f02\u6b65 Python \u667a\u80fd\u4f53\u7684\u8fd0\u884c\u6210\u672c\u6b63\u5728\u4e0b\u964d",
        "\u961f\u5217\u9a71\u52a8",
        "\u66f4\u597d\u7684\u961f\u5217",
    ]:
        assert marker in semantic_text
    for fragment in ["\u6d93", "\u934f", "\u93c3", "\u9427", "\u7025", "\u95ab", "\u5bb8", "\u9396", "\ufffd"]:
        assert fragment not in semantic_text
