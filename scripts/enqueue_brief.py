from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "shared"))
sys.path.insert(0, str(ROOT / "workers" / "briefs"))

try:
    from arq import create_pool  # noqa: E402
    from arq.connections import RedisSettings  # noqa: E402
except ImportError as exc:  # noqa: E402
    raise SystemExit("arq is required to enqueue brief jobs; install project dependencies first") from exc
from jobs import redis_settings  # noqa: E402


async def enqueue(job_name: str, **kwargs) -> str:
    settings = redis_settings()
    pool = await create_pool(RedisSettings(host=settings["host"], port=settings["port"], database=settings["database"]))
    try:
        job = await pool.enqueue_job(job_name, **kwargs)
        if job is None:
            raise RuntimeError(f"failed to enqueue {job_name}")
        return job.job_id
    finally:
        await pool.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Enqueue CodePick L3 brief jobs into Arq.")
    parser.add_argument("--type", choices=["public", "personal"], default="public")
    parser.add_argument("--vertical")
    parser.add_argument("--user-id", type=int)
    parser.add_argument("--email")
    args = parser.parse_args()

    if args.type == "personal" and (args.user_id is None or not args.email):
        raise SystemExit("--user-id and --email are required for personal briefs")

    if args.type == "public":
        job_id = asyncio.run(enqueue("generate_public_brief_job", vertical=args.vertical))
    else:
        job_id = asyncio.run(enqueue("generate_personal_brief_job", user_id=args.user_id, email=args.email, vertical=args.vertical))
    print(f"enqueued {args.type} brief job: {job_id}")


if __name__ == "__main__":
    main()
