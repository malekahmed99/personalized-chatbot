import asyncio
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool

from alembic import context

# ── Load our app config so we read DB_URL from backend/.env ──────────────────
# Explicitly resolve the .env path relative to this file so Alembic works
# regardless of the working directory it is invoked from.
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from core.config import settings

# ── Import all models so autogenerate can detect every table ─────────────────
import models  # noqa: F401 — side-effect import registers ORM metadata
from core.database import Base

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ── Offline mode ──────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL to stdout)."""
    context.configure(
        url=settings.db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online (async) mode ───────────────────────────────────────────────────────
def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations inside it."""
    connectable = create_async_engine(settings.db_url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ── Entry point ───────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
