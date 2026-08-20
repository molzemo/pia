"""
Thin database layer.

We use SQLAlchemy Core (not the ORM) with raw parameterised SQL. The schema
is small, mostly JSONB-driven (agent memory, permissions, carts) and this
keeps the query logic easy to read next to the SQL in schema.sql.
"""
import json
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from .config import settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        if not settings.DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL is not set. Point it at your Supabase Postgres "
                "connection string (Project Settings -> Database -> Connection string)."
            )
        # NullPool: Railway/Render + Supabase pooler already manage connections;
        # avoids stale connections across container sleep/wake cycles.
        _engine = create_engine(settings.DATABASE_URL, poolclass=NullPool, future=True)
    return _engine


@contextmanager
def conn():
    engine = get_engine()
    with engine.connect() as c:
        yield c
        c.commit()


def q(connection, sql: str, **params):
    """Run a SQL statement and return a list of dict rows."""
    result = connection.execute(text(sql), params)
    if result.returns_rows:
        return [dict(row._mapping) for row in result]
    return []


def q_one(connection, sql: str, **params):
    rows = q(connection, sql, **params)
    return rows[0] if rows else None


def to_jsonb(value) -> str:
    return json.dumps(value)
