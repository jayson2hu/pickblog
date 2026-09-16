from __future__ import annotations

import os

from .config import get_settings


def _configured(value: str | None) -> bool:
    return bool(value and value.strip())


def _not_default(value: str, default: str) -> bool:
    return bool(value.strip()) and value != default


def _postgres_database_url(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    return normalized.startswith("postgresql://") or normalized.startswith("postgresql+")


def _https_url(value: str | None) -> bool:
    return bool((value or "").strip().lower().startswith("https://"))


def _int_env(name: str, default: str) -> int | None:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return None


def l3_readiness() -> dict:
    settings = get_settings()
    repository_backend = os.getenv("L3_REPOSITORY_BACKEND", "memory").lower()
    quota_backend = os.getenv("L3_QUOTA_BACKEND", repository_backend).lower()
    use_real_l2 = not settings.l3_use_stub_l2
    production_billing = settings.billing_environment == "production"
    email_provider = settings.email_provider.lower()
    auth_login_mode = settings.auth_login_mode
    database_url = os.getenv("DATABASE_URL")
    redis_host = os.getenv("ARQ_REDIS_HOST", "127.0.0.1")
    redis_port = _int_env("ARQ_REDIS_PORT", "6379")
    redis_database = _int_env("ARQ_REDIS_DATABASE", "0")
    redis_explicit = _configured(os.getenv("ARQ_REDIS_HOST")) and _configured(os.getenv("ARQ_REDIS_PORT"))
    final_like = (
        use_real_l2
        or repository_backend == "sqlalchemy"
        or quota_backend == "sqlalchemy"
        or production_billing
        or email_provider in {"resend", "ses"}
    )

    checks = {
        "auth": {
            "login_mode": auth_login_mode,
            "ready": auth_login_mode == "external" or (not final_like and auth_login_mode == "development"),
        },
        "content_provider": {
            "mode": "stub" if settings.l3_use_stub_l2 else "l2-http",
            "ready": not use_real_l2 or _https_url(settings.l2_base_url),
        },
        "repository": {
            "backend": repository_backend,
            "ready": repository_backend != "sqlalchemy" or _postgres_database_url(database_url),
        },
        "quota": {
            "backend": quota_backend,
            "ready": quota_backend != "sqlalchemy" or _postgres_database_url(database_url),
        },
        "billing": {
            "environment": settings.billing_environment,
            "ready": (
                not production_billing
                or (
                    _https_url(settings.paddle_checkout_base_url)
                    and not settings.paddle_checkout_base_url.startswith("https://sandbox-payments.")
                    and _not_default(settings.paddle_webhook_secret, "dev-webhook-secret")
                )
            ),
        },
        "email": {
            "provider": email_provider,
            "ready": (
                email_provider == "mock"
                or (email_provider == "resend" and _configured(settings.resend_api_key) and _configured(settings.email_from))
                or (email_provider == "ses" and _configured(settings.ses_region) and _configured(settings.email_from))
            ),
        },
        "secrets": {
            "jwt_secret": "configured" if _not_default(settings.jwt_secret, "dev-secret") else "default",
            "paddle_webhook_secret": "configured" if _not_default(settings.paddle_webhook_secret, "dev-webhook-secret") else "default",
            "ready": (not final_like) or (_not_default(settings.jwt_secret, "dev-secret") and _not_default(settings.paddle_webhook_secret, "dev-webhook-secret")),
        },
        "worker": {
            "redis_host": redis_host,
            "redis_port": redis_port,
            "redis_database": redis_database,
            "ready": (not final_like or redis_explicit) and redis_port is not None and redis_database is not None,
        },
    }

    return {
        "status": "ready" if all(check["ready"] for check in checks.values()) else "degraded",
        "service": "l3",
        "checks": checks,
    }
