import pytest

from datetime import datetime
from fastapi import FastAPI
from pytest_mock import MockerFixture
from unittest.mock import Mock

from entities.models import FilingPeriodDAO, FilingType


@pytest.fixture
def app_fixture(mocker: MockerFixture) -> FastAPI:
    mocked_engine = mocker.patch("sqlalchemy.ext.asyncio.create_async_engine")
    MockedEngine = mocker.patch("sqlalchemy.ext.asyncio.AsyncEngine")
    mocked_engine.return_value = MockedEngine.return_value
    from main import app

    return app


@pytest.fixture
def get_institutions_mock(mocker: MockerFixture) -> Mock:
    mock = mocker.patch("entities.repos.submission_repo.get_filing_periods")
    mock.return_value = [
        FilingPeriodDAO(
            name="FilingPeriod2024",
            start_period=datetime.now(),
            end_period=datetime.now(),
            due=datetime.now(),
            filing_type=FilingType.MANUAL,
        )
    ]
    return mock
