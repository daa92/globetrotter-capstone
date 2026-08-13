"""
app/db.py

Phase 2 persistence: a single generic `store` table backs every
"collection" that used to be its own JSON file (see app/storage.py for
why — this is a deliberate 1:1 semantic swap so no router/business-logic
code anywhere else had to change).

Uses SQLAlchemy Core (no ORM models) against DATABASE_URL:
  - Production (Render): a TiDB connection string, e.g.
    mysql+pymysql://user:password@host:4000/globetrotter
  - Local dev / tests (DATABASE_URL unset): falls back to a local SQLite
    file, so `uvicorn app.main:app` still works with zero setup.

SQLAlchemy's `metadata.create_all()` generates correct dialect-specific
DDL for either backend (AUTO_INCREMENT vs SQLite's rowid, JSON type
handling, etc.) — that's the whole reason this is defined as a Core
Table rather than raw CREATE TABLE SQL.

`engine` is looked up as a module attribute (`db.engine`) everywhere it's
used, rather than imported by value (`from app.db import engine`), so
tests can swap it out via monkeypatch — see tests/conftest.py.
"""
import ssl as ssl_module

from sqlalchemy import JSON, Column, Integer, MetaData, String, Table, create_engine

from app.config import settings

metadata = MetaData()

store = Table(
    "store",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("collection", String(64), nullable=False, index=True),
    Column("data", JSON, nullable=False),
)


def _make_engine():
    url = settings.DATABASE_URL or "sqlite:///./local_dev.db"

    connect_args = {}
    if url.startswith("mysql"):
        # TiDB requires TLS. Verifying against the system CA bundle (via
        # certifi) matches TiDB Cloud's documented Python connection
        # approach for PyMySQL.
        import certifi

        connect_args = {
            "ssl": {"ca": certifi.where()},
        }

    return create_engine(
        url,
        pool_pre_ping=True,  # TiDB Serverless can idle-close connections; ping avoids stale "MySQL server has gone away" errors
        pool_recycle=280,
        connect_args=connect_args,
    )


engine = _make_engine()


def init_db() -> None:
    """Create the `store` table if it doesn't exist yet. Safe to call on
    every app startup (idempotent) — see lifespan in app/__init__.py."""
    metadata.create_all(engine)
