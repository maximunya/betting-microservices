from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.database import DATABASE_URL, get_async_session, metadata
from app.main import app


@pytest_asyncio.fixture(scope="session")
async def engine():
    # NullPool: a session-scoped engine's pooled connections would otherwise
    # get reused across tests that each run on their own pytest-asyncio event
    # loop, which asyncpg rejects ("attached to a different loop").
    test_engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    async with test_engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)
        await conn.run_sync(metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    async with engine.connect() as conn:
        trans = await conn.begin()
        async_session = async_sessionmaker(bind=conn, expire_on_commit=False)
        async with async_session() as sess:
            yield sess
        await trans.rollback()


@pytest_asyncio.fixture
async def client(session) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_async_session():
        yield session

    app.dependency_overrides[get_async_session] = override_get_async_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
