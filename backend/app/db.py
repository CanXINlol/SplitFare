from __future__ import annotations

import os
import tempfile
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DEFAULT_DATABASE_URL = f"sqlite:///{os.path.join(tempfile.gettempdir(), 'splitfare.db')}"


class Base(DeclarativeBase):
    pass


def database_url_from_env() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def make_engine(database_url: str | None = None):
    url = database_url or database_url_from_env()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_database() -> None:
    import app.db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
