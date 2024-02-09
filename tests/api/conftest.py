import pytest

from datetime import datetime
from fastapi import FastAPI
from pytest_mock import MockerFixture
from unittest.mock import Mock

from entities.models import FilingPeriodDAO, FilingType, FilingDAO, FilingTaskStateDAO, FilingTaskState, FilingTaskDAO
from entities.repos import submission_repo as repo


@pytest.fixture
def app_fixture(mocker: MockerFixture) -> FastAPI:
    from main import app

    return app


@pytest.fixture
def get_filing_period_mock(mocker: MockerFixture) -> Mock:
    mock = mocker.patch("entities.repos.submission_repo.get_filing_periods")
    mock.return_value = [
        FilingPeriodDAO(
            name="FilingPeriod2024",
            start_period=datetime.now(),
            end_period=datetime.now(),
            due=datetime.now(),
            filing_type=FilingType.ANNUAL,
        )
    ]
    return mock


@pytest.fixture
def get_filings_mock(mocker: MockerFixture) -> Mock:
    mock = mocker.patch("entities.repos.submission_repo.get_period_filings_for_user")
    mock.return_value = [
        FilingDAO(
            id=1,
            lei="12345678",
            tasks=[
                FilingTaskStateDAO(
                    filing=1,
                    task=FilingTaskDAO(name="Task-1", task_order=1),
                    state=FilingTaskState.NOT_STARTED,
                    user="",
                ),
                FilingTaskStateDAO(
                    filing=1,
                    task=FilingTaskDAO(name="Task-2", task_order=2),
                    state=FilingTaskState.NOT_STARTED,
                    user="",
                ),
            ],
            filing_period=1,
            institution_snapshot_id="v1",
            contact_info="test@cfpb.gov",
        )
    ]
    return mock


@pytest.fixture
def get_filings_error_mock(mocker: MockerFixture) -> Mock:
    mock = mocker.patch(
        "entities.repos.submission_repo.get_period_filings_for_user",
        side_effect=repo.NoFilingPeriodException(
            "There is no Filing Period with name FilingPeriod2025 defined in the database."
        ),
    )
    return mock
