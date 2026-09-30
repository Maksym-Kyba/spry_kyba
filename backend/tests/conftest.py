import json
import os
import time
from collections.abc import AsyncIterator, Callable

import asyncpg
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth import TokenVerifier, get_verifier
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


# Tokens are signed with a throwaway key; the verifier gets it as a preloaded JWKS, exactly as
# on AWS, so no test talks to Cognito.
POOL_ID = "us-east-1_TestPool"
CLIENT_ID = "test-client"
ISSUER = f"https://cognito-idp.us-east-1.amazonaws.com/{POOL_ID}"
KID = "test-key"
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
JWKS = json.dumps(
    {
        "keys": [
            {
                **json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(PRIVATE_KEY.public_key())),
                "kid": KID,
                "alg": "RS256",
                "use": "sig",
            }
        ]
    }
)

TokenFactory = Callable[..., str]


def make_token(sub: str = "alice", **claims) -> str:
    """A Cognito-style ID token; keyword arguments override or add claims."""
    now = int(time.time())
    payload = {
        "sub": sub,
        "email": f"{sub}@example.com",
        "name": sub.title(),
        "token_use": "id",
        "aud": CLIENT_ID,
        "iss": ISSUER,
        "iat": now,
        "exp": now + 3600,
        **claims,
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256", headers={"kid": KID})


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


@pytest.fixture(scope="session")
async def engine():
    await _ensure_database(TEST_DATABASE_URL)
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def client(engine) -> AsyncIterator[AsyncClient]:
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            yield session

    verifier = TokenVerifier(POOL_ID, CLIENT_ID, JWKS)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_verifier] = lambda: verifier
    # Signed in as "alice"; tests pass other headers to act as someone else.
    headers = {"Authorization": f"Bearer {make_token('alice')}"}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=headers
    ) as client:
        yield client
    app.dependency_overrides.clear()
