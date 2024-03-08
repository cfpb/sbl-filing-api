import pytest

from datetime import datetime
from fastapi import FastAPI
from pytest_mock import MockerFixture
from unittest.mock import Mock
import pandas as pd

from entities.models import (
    FilingPeriodDAO,
    FilingType,
    FilingDAO,
    ContactInfoDAO,
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
        filing_period="2024",
        institution_snapshot_id="v1",
        contact_info=ContactInfoDAO(
            id=1,
            filing=1,
            first_name="test_first_name_1",
            last_name="test_last_name_1",
            hq_address_street_1="address street 1",
            hq_address_street_2="address street 2",
            hq_address_city="Test City",
            hq_address_state="TS",
            hq_address_zip="12345",
            phone="112-345-6789",
            email="test1@cfpb.gov",
        ),
    )
    return mock


@pytest.fixture
def post_filing_mock(mocker: MockerFixture) -> Mock:
    mock = mocker.patch("entities.repos.submission_repo.create_new_filing")
    mock.return_value = FilingDAO(
        id=3,
        lei="ZXWVUTSRQP",
        filing_period="2024",
        institution_snapshot_id="v1",
        contact_info=ContactInfoDAO(
            id=3,
            filing=3,
            first_name="test_first_name_3",
            last_name="test_last_name_3",
            hq_address_street_1="address street 1",
            hq_address_street_2="",
            hq_address_city="Test City",
            hq_address_state="TS",
            hq_address_zip="12345",
            phone="312-345-6789",
            email="test3@cfpb.gov",
        ),
    )
    return mock


@pytest.fixture(scope="session")
def submission_csv(tmpdir_factory) -> str:
    df = pd.DataFrame([["0", "1"]], columns=["Submission_Column_1", "Submission_Column_2"])
    filename = str(tmpdir_factory.mktemp("data").join("submission.csv"))
    df.to_csv(filename)
    return filename
