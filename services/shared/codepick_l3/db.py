from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@lru_cache
def get_engine():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required for SQLAlchemy repository mode")
    return create_engine(url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def session_scope() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

