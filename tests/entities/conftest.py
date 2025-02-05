import asyncio
import pytest

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from unittest.mock import Mock
from sbl_filing_api.entities.models.dao import Base
from regtech_api_commons.models.auth import AuthenticatedUser


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture(scope="session")
def engine():
    return create_engine("sqlite://")


@pytest.fixture(scope="function", autouse=True)
def setup_db(
    request: pytest.FixtureRequest,
    engine: Engine,
):
    Base.metadata.create_all(engine)

    def teardown():
        Base.metadata.drop_all(engine)

    request.addfinalizer(teardown)


@pytest.fixture(scope="function")
def transaction_session(session_generator: scoped_session):
    with session_generator() as session:
        yield session


@pytest.fixture(scope="function")
def query_session(session_generator: scoped_session):
    with session_generator() as session:
        yield session


@pytest.fixture(scope="function")
def session_generator(engine: Engine):
    return scoped_session(sessionmaker(engine, expire_on_commit=False))


@pytest.fixture
def authed_user_mock() -> Mock:
    claims = {
        "name": "Test User",
        "preferred_username": "test_user",
        "email": "test@local.host",
        "institutions": ["123456ABCDEF", "654321FEDCBA"],
        "sub": "123456-7890-ABCDEF-GHIJ",
    }
    return AuthenticatedUser.from_claim(claims)
