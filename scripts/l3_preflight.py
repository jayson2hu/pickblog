from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "shared"))


def _configured(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def _not_default_secret(name: str, default: str) -> bool:
    value = os.getenv(name, "")
    return bool(value.strip()) and value != default


def _postgres_database_url() -> bool:
    value = os.getenv("DATABASE_URL", "").strip().lower()
    return value.startswith("postgresql://") or value.startswith("postgresql+")


def _https_url(name: str) -> bool:
    return os.getenv(name, "").strip().lower().startswith("https://")


def _check(name: str, ready: bool, detail: str) -> dict:
    return {"name": name, "ready": ready, "detail": detail}


def evaluate_preflight(final: bool = False) -> dict:
    repository_backend = os.getenv("L3_REPOSITORY_BACKEND", "memory").lower()
    quota_backend = os.getenv("L3_QUOTA_BACKEND", repository_backend).lower()
    email_provider = os.getenv("EMAIL_PROVIDER", "mock").lower()
    billing_environment = os.getenv("BILLING_ENVIRONMENT", "sandbox").lower()
    use_stub_l2 = os.getenv("L3_USE_STUB_L2", "true").lower() == "true"
    database_ready = _postgres_database_url() if final else _configured("DATABASE_URL")

    checks = [
        _check("jwt_secret", not final or _not_default_secret("JWT_SECRET", "dev-secret"), "JWT_SECRET must be non-default for final integration"),
        _check(
            "content_provider",
            (use_stub_l2 and not final) or ((not use_stub_l2) and _https_url("L2_BASE_URL")),
            "dev uses stub L2; final requires L3_USE_STUB_L2=false and HTTPS L2_BASE_URL",
        ),
        _check(
            "repository",
            (repository_backend == "memory" and not final) or (repository_backend == "sqlalchemy" and database_ready),
            "dev may use memory; final requires L3_REPOSITORY_BACKEND=sqlalchemy and PostgreSQL DATABASE_URL",
        ),
        _check(
            "quota",
            (quota_backend == "memory" and not final) or (quota_backend == "sqlalchemy" and database_ready),
            "dev may use memory; final requires L3_QUOTA_BACKEND=sqlalchemy and PostgreSQL DATABASE_URL",
        ),
        _check(
            "billing",
            (billing_environment == "sandbox" and not final)
            or (
                billing_environment == "production"
                and _https_url("PADDLE_CHECKOUT_BASE_URL")
                and not os.getenv("PADDLE_CHECKOUT_BASE_URL", "").startswith("https://sandbox-payments.")
                and _not_default_secret("PADDLE_WEBHOOK_SECRET", "dev-webhook-secret")
            ),
            "dev uses sandbox; final requires HTTPS production Paddle URL and non-default webhook secret",
        ),
        _check(
            "email",
            (email_provider == "mock" and not final)
            or (email_provider == "resend" and _configured("RESEND_API_KEY") and _configured("EMAIL_FROM"))
            or (email_provider == "ses" and _configured("SES_REGION") and _configured("EMAIL_FROM")),
            "dev may use mock; final requires Resend or SES configuration",
        ),
        _check(
            "redis",
            (_configured("ARQ_REDIS_HOST") and _configured("ARQ_REDIS_PORT")) if final else bool(os.getenv("ARQ_REDIS_HOST", "127.0.0.1").strip()) and bool(os.getenv("ARQ_REDIS_PORT", "6379").strip()),
            "dev may use localhost Redis defaults; final requires explicit ARQ_REDIS_HOST and ARQ_REDIS_PORT",
        ),
        _check("pricing", os.getenv("PRICE_PRO_MONTH_USD", "8") == "8" and os.getenv("PRICE_PRO_YEAR_USD", "79") == "79" and os.getenv("PRICE_EARLYBIRD_USD", "4.9") == "4.9", "USD price invariants must match L3 spec"),
    ]
    ready = all(check["ready"] for check in checks)
    return {"status": "ready" if ready else "blocked", "mode": "final" if final else "dev", "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate CodePick L3 runtime configuration.")
    parser.add_argument("--final", action="store_true", help="Require final integration configuration instead of independent dev defaults.")
    args = parser.parse_args()
    report = evaluate_preflight(final=args.final)
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] != "ready":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
