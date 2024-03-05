import pytest

from datetime import datetime
from fastapi import FastAPI
from pytest_mock import MockerFixture
from unittest.mock import Mock

from entities.models import (
    FilingPeriodDAO,
    FilingType,
    FilingDAO,
    FilingTaskProgressDAO,
    FilingTaskState,
    FilingTaskDAO,
)

from regtech_api_commons.models.auth import AuthenticatedUser
from starlette.authentication import AuthCredentials, UnauthenticatedUser


@pytest.fixture
def app_fixture(mocker: MockerFixture) -> FastAPI:
    from main import app

    return app


@pytest.fixture
def auth_mock(mocker: MockerFixture) -> Mock:
    return mocker.patch("regtech_api_commons.oauth2.oauth2_backend.BearerTokenAuthBackend.authenticate")


@pytest.fixture
def authed_user_mock(auth_mock: Mock) -> Mock:
    claims = {
        "name": "test",
        "preferred_username": "test_user",
        "email": "test@local.host",
        "institutions": "123456ABCDEF, 654321FEDCBA",
    }
    auth_mock.return_value = (
        AuthCredentials(["authenticated"]),
        AuthenticatedUser.from_claim(claims),
    )
    return auth_mock


@pytest.fixture
def unauthed_user_mock(auth_mock: Mock) -> Mock:
    auth_mock.return_value = (AuthCredentials("unauthenticated"), UnauthenticatedUser())
    return auth_mock


@pytest.fixture
def get_filing_period_mock(mocker: MockerFixture) -> Mock:
    mock = mocker.patch("entities.repos.submission_repo.get_filing_periods")
    mock.return_value = [
        FilingPeriodDAO(
            code="2024",
            description="Filing Period 2024",
            start_period=datetime.now(),
            end_period=datetime.now(),
            due=datetime.now(),
            filing_type=FilingType.ANNUAL,
        )
    ]
    return mock


@pytest.fixture
def get_filing_mock(mocker: MockerFixture) -> Mock:
    mock = mocker.patch("entities.repos.submission_repo.get_filing")
    mock.return_value = FilingDAO(
        id=1,
        lei="1234567890",
        tasks=[
            FilingTaskProgressDAO(
                id=1,
                filing=1,
                task=FilingTaskDAO(name="Task-1", task_order=1),
                state=FilingTaskState.NOT_STARTED,
                user="",
            ),
            FilingTaskProgressDAO(
                id=2,
                filing=1,
                task=FilingTaskDAO(name="Task-2", task_order=2),
                state=FilingTaskState.NOT_STARTED,
                user="",
            ),
        ],
        filing_period="2024",
        institution_snapshot_id="v1",
        contact_info="test@cfpb.gov",
    )
    return mock


@pytest.fixture
def post_filing_mock(mocker: MockerFixture) -> Mock:
    mock = mocker.patch("entities.repos.submission_repo.create_new_filing")
    mock.return_value = FilingDAO(
        id=3,
        lei="ZXWVUTSRQP",
        tasks=[
            FilingTaskProgressDAO(
                id=1,
                filing=3,
                task=FilingTaskDAO(name="Task-1", task_order=1),
                state=FilingTaskState.NOT_STARTED,
                user="",
            ),
            FilingTaskProgressDAO(
                id=2,
                filing=3,
                task=FilingTaskDAO(name="Task-2", task_order=2),
                state=FilingTaskState.NOT_STARTED,
                user="",
            ),
        ],
        filing_period="2024",
        institution_snapshot_id="v1",
    )
    return mock
