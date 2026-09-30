import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db import get_session
from app.main import app
from app.models import Base

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    make_url(settings.database_url)
    .set(database=f"{make_url(settings.database_url).database}_test")
    .render_as_string(hide_password=False),
)


async def _ensure_database(url: str) -> None:
    parsed = make_url(url)
    conn = await asyncpg.connect(
        user=parsed.username,
        password=parsed.password,
        host=parsed.host,
        port=parsed.port or 5432,
        database="postgres",
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", parsed.database
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{parsed.database}"')
    finally:
        await conn.close()


def _run_migrations(url: str, downgrade: bool = False) -> None:
    alembic_ini = Path(__file__).resolve().parent.parent / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini))
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    if downgrade:
        command.downgrade(alembic_cfg, "base")
    else:
        command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="session")
async def engine():
    await _ensure_database(TEST_DATABASE_URL)
    # Schema is created and modified exclusively through Alembic migrations
    # (Base.metadata.create_all is forbidden).
    await asyncio.to_thread(_run_migrations, TEST_DATABASE_URL, False)

    engine = create_async_engine(TEST_DATABASE_URL)
    yield engine
    await engine.dispose()
    await asyncio.to_thread(_run_migrations, TEST_DATABASE_URL, True)


@pytest.fixture
async def client(engine) -> AsyncIterator[AsyncClient]:
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()
