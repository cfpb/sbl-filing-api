import asyncio
import pytest

from asyncio import current_task
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    async_scoped_session,
    async_sessionmaker,
)
from entities.models import Base


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture(scope="session")
def engine():
    return create_async_engine("sqlite+aiosqlite://")


@pytest.fixture(scope="function", autouse=True)
async def setup_db(
    request: pytest.FixtureRequest,
    engine: AsyncEngine,
    event_loop: asyncio.AbstractEventLoop,
):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    def teardown():
        async def td():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)

        event_loop.run_until_complete(td())

    request.addfinalizer(teardown)


@pytest.fixture(scope="function")
async def transaction_session(session_generator: async_scoped_session):
    async with session_generator() as session:
        yield session


@pytest.fixture(scope="function")
async def query_session(session_generator: async_scoped_session):
    async with session_generator() as session:
        yield session


@pytest.fixture(scope="function")
def session_generator(engine: AsyncEngine):
    return async_scoped_session(async_sessionmaker(engine, expire_on_commit=False), current_task)
