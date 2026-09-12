import os
from dataclasses import dataclass

try:
    from arq.cron import cron
except ImportError:
    @dataclass
    class CronFallback:
        coroutine: object
        hour: int
        minute: int
        run_at_startup: bool

        @property
        def name(self) -> str:
            return getattr(self.coroutine, "__name__", "unknown")

    def cron(coroutine, *, hour: int, minute: int, run_at_startup: bool = False):
        return CronFallback(coroutine=coroutine, hour=hour, minute=minute, run_at_startup=run_at_startup)

from codepick_l3.briefs import generate_personal_brief, generate_public_brief
from codepick_l3.email import get_email_client
from codepick_l3.provider import get_content_provider
from codepick_l3.repository import get_repository
from codepick_l3.schemas import User


async def generate_public_brief_job(ctx: dict, vertical: str | None = None) -> dict:
    brief = generate_public_brief(get_content_provider(), vertical=vertical)
    get_repository().save_brief(brief)
    return brief.model_dump(mode="json")


async def generate_personal_brief_job(ctx: dict, user_id: int, email: str, vertical: str | None = None) -> dict:
    user = User(id=user_id, email=email, plan="pro")
    brief = generate_personal_brief(get_content_provider(), user=user, vertical=vertical)
    get_repository().save_brief(brief)
    delivery = get_email_client().send_brief(email, brief)
    data = brief.model_dump(mode="json")
    data["delivery"] = delivery.__dict__
    return data


def redis_settings() -> dict:
    return {
        "host": os.getenv("ARQ_REDIS_HOST", "127.0.0.1"),
        "port": int(os.getenv("ARQ_REDIS_PORT", "6379")),
        "database": int(os.getenv("ARQ_REDIS_DATABASE", "0")),
    }


def brief_cron_jobs() -> list:
    hour = int(os.getenv("BRIEF_PUBLIC_CRON_HOUR_UTC", "0"))
    minute = int(os.getenv("BRIEF_PUBLIC_CRON_MINUTE_UTC", "0"))
    return [
        cron(
            generate_public_brief_job,
            name="generate_public_brief_job",
            hour=hour,
            minute=minute,
            run_at_startup=os.getenv("BRIEF_RUN_AT_STARTUP", "false").lower() == "true",
        )
    ]


class WorkerSettings:
    functions = [generate_public_brief_job, generate_personal_brief_job]
    cron_jobs = brief_cron_jobs()
    redis_settings = redis_settings()
    max_jobs = int(os.getenv("ARQ_MAX_JOBS", "4"))
    job_timeout = int(os.getenv("ARQ_JOB_TIMEOUT_SECONDS", "120"))
