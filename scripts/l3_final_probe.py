from __future__ import annotations

import argparse
import asyncio
from datetime import date
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable

from sqlalchemy import inspect, text


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "shared"))
sys.path.insert(0, str(ROOT / "workers" / "briefs"))

from l3_preflight import evaluate_preflight  # noqa: E402

from codepick_l3.config import get_settings, reset_settings_cache  # noqa: E402
from codepick_l3.email import get_email_client  # noqa: E402
from codepick_l3.models import Base  # noqa: E402
from codepick_l3.provider import get_content_provider  # noqa: E402
from codepick_l3.schemas import Brief  # noqa: E402


def _check(name: str, ready: bool, detail: str, **metadata: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": name, "ready": ready, "detail": detail}
    if metadata:
        payload["metadata"] = metadata
    return payload


def _run_check(name: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = fn()
    except Exception as exc:
        result = _check(name, False, f"{type(exc).__name__}: {exc}")
    result["duration_ms"] = round((time.monotonic() - started) * 1000, 2)
    return result


def check_preflight() -> dict[str, Any]:
    report = evaluate_preflight(final=True)
    blocked = [check["name"] for check in report["checks"] if not check["ready"]]
    return _check(
        "final_preflight",
        report["status"] == "ready",
        "final preflight ready" if report["status"] == "ready" else f"blocked checks: {', '.join(blocked)}",
        blocked=blocked,
    )


def check_l2_provider() -> dict[str, Any]:
    provider = get_content_provider()
    page = provider.list(status="COMPLETED", limit=1)
    if not page.items:
        return _check("l2_provider", False, "L2 returned no COMPLETED content from /content")
    summary = page.items[0]
    detail = provider.get(summary.id)
    if detail.status != "COMPLETED":
        return _check("l2_provider", False, f"L2 detail {detail.id} status is {detail.status}, expected COMPLETED")
    return _check("l2_provider", True, "L2 list/get returned COMPLETED content", content_id=detail.id, total=page.total)


def check_database() -> dict[str, Any]:
    from codepick_l3.db import get_engine

    engine = get_engine()
    expected_tables = sorted(Base.metadata.tables.keys())
    with engine.connect() as connection:
        connection.execute(text("SELECT 1")).scalar_one()
        existing = set(inspect(connection).get_table_names())
    missing = [table for table in expected_tables if table not in existing]
    required_taxonomy_tables = ["taxonomy_categories", "audiences", "audience_categories"]
    missing.extend([table for table in required_taxonomy_tables if table not in existing and table not in missing])
    return _check(
        "database",
        not missing,
        "PostgreSQL connection and L3-owned tables ready" if not missing else f"missing L3-owned tables: {', '.join(missing)}",
        database_url=os.getenv("DATABASE_URL", "").split("@")[-1],
        missing=missing,
    )


def check_quota_database() -> dict[str, Any]:
    if os.getenv("L3_QUOTA_BACKEND", os.getenv("L3_REPOSITORY_BACKEND", "memory")).lower() != "sqlalchemy":
        return _check("quota_database", False, "L3_QUOTA_BACKEND must be sqlalchemy for final integration")
    from codepick_l3.db import get_engine

    with get_engine().connect() as connection:
        existing = set(inspect(connection).get_table_names())
        missing = [table for table in ["api_keys", "api_usage_daily"] if table not in existing]
    return _check(
        "quota_database",
        not missing,
        "SQLAlchemy quota tables ready" if not missing else f"missing quota tables: {', '.join(missing)}",
        missing=missing,
    )


async def _redis_ping() -> dict[str, Any]:
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
    except ImportError as exc:
        return _check("redis_arq", False, "arq is required for Redis/Arq final probe", error=str(exc))
    from jobs import redis_settings

    settings = redis_settings()
    pool = await create_pool(RedisSettings(host=settings["host"], port=settings["port"], database=settings["database"]))
    try:
        pong = await pool.ping()
    finally:
        await pool.close()
    return _check("redis_arq", bool(pong), "Redis/Arq ping ready", host=settings["host"], port=settings["port"], database=settings["database"])


def check_redis() -> dict[str, Any]:
    if not os.getenv("ARQ_REDIS_HOST") or not os.getenv("ARQ_REDIS_PORT"):
        return _check("redis_arq", False, "ARQ_REDIS_HOST and ARQ_REDIS_PORT must be explicit for final integration")
    return asyncio.run(_redis_ping())


def check_email_config() -> dict[str, Any]:
    settings = get_settings()
    client = get_email_client()
    provider = getattr(client, "provider", settings.email_provider)
    configured = settings.email_provider in {"resend", "ses"}
    return _check(
        "email_provider",
        configured,
        f"{provider} email client configured" if configured else "EMAIL_PROVIDER must be resend or ses for final integration",
        provider=provider,
        sender=settings.email_from,
    )


def _probe_brief() -> Brief:
    provider = get_content_provider()
    page = provider.list(status="COMPLETED", limit=1)
    return Brief(
        id=f"final-probe-{date.today().isoformat()}",
        user_id=None,
        vertical_code=None,
        brief_date=date.today().isoformat(),
        items=page.items[:1],
        channels={"email": True, "probe": True},
        status="generated",
    )


def check_send_email(to: str) -> dict[str, Any]:
    delivery = get_email_client().send_brief(to, _probe_brief())
    return _check(
        "email_delivery",
        delivery.status in {"queued", "sent"},
        f"email provider accepted test brief for {to}",
        provider=delivery.provider,
        status=delivery.status,
    )


async def _enqueue_public_brief(vertical: str | None) -> dict[str, Any]:
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
    except ImportError as exc:
        return _check("brief_enqueue", False, "arq is required to enqueue brief jobs", error=str(exc))
    from jobs import redis_settings

    settings = redis_settings()
    pool = await create_pool(RedisSettings(host=settings["host"], port=settings["port"], database=settings["database"]))
    try:
        job = await pool.enqueue_job("generate_public_brief_job", vertical=vertical)
    finally:
        await pool.close()
    return _check("brief_enqueue", job is not None, "public brief job enqueued", job_id=getattr(job, "job_id", None), vertical=vertical)


def check_enqueue_public_brief(vertical: str | None) -> dict[str, Any]:
    return asyncio.run(_enqueue_public_brief(vertical))


def check_paddle_config() -> dict[str, Any]:
    settings = get_settings()
    production_url = settings.paddle_checkout_base_url.startswith("https://") and not settings.paddle_checkout_base_url.startswith("https://sandbox-payments.")
    ready = settings.billing_environment == "production" and production_url and settings.paddle_webhook_secret != "dev-webhook-secret"
    return _check(
        "paddle_config",
        ready,
        "production Paddle checkout and webhook configuration present" if ready else "production Paddle checkout and webhook configuration missing",
        environment=settings.billing_environment,
        checkout_host=settings.paddle_checkout_base_url.split("/")[2] if "://" in settings.paddle_checkout_base_url else settings.paddle_checkout_base_url,
    )


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    reset_settings_cache()
    preflight = _run_check("final_preflight", check_preflight)
    if not preflight["ready"]:
        return {
            "status": "blocked",
            "mode": "final",
            "side_effects": {
                "email_delivery": False,
                "brief_enqueue": False,
            },
            "checks": [preflight],
        }
    checks = [
        preflight,
        _run_check("l2_provider", check_l2_provider),
        _run_check("database", check_database),
        _run_check("quota_database", check_quota_database),
        _run_check("redis_arq", check_redis),
        _run_check("email_provider", check_email_config),
        _run_check("paddle_config", check_paddle_config),
    ]
    if args.send_test_email:
        checks.append(_run_check("email_delivery", lambda: check_send_email(args.send_test_email)))
    if args.enqueue_brief:
        checks.append(_run_check("brief_enqueue", lambda: check_enqueue_public_brief(args.vertical)))
    ready = all(check["ready"] for check in checks)
    return {
        "status": "ready" if ready else "blocked",
        "mode": "final",
        "side_effects": {
            "email_delivery": bool(args.send_test_email),
            "brief_enqueue": bool(args.enqueue_brief),
        },
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run live CodePick L3 final integration probes.")
    parser.add_argument("--send-test-email", metavar="EMAIL", help="Send a real provider test brief to EMAIL.")
    parser.add_argument("--enqueue-brief", action="store_true", help="Enqueue a public brief job into the configured Redis/Arq runtime.")
    parser.add_argument("--vertical", help="Optional vertical for --enqueue-brief.")
    args = parser.parse_args()

    report = build_report(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] != "ready":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
