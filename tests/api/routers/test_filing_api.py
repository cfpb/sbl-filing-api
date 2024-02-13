import datetime

from unittest.mock import ANY, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from entities.models import SubmissionDAO, SubmissionState


class TestFilingApi:
    def test_unauthed_get_periods(
        self, mocker: MockerFixture, app_fixture: FastAPI, get_filing_period_mock: Mock, unauthed_user_mock: Mock
    ):
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/periods")
        assert res.status_code == 403

    def test_get_periods(
        self, mocker: MockerFixture, app_fixture: FastAPI, get_filing_period_mock: Mock, authed_user_mock: Mock
    ):
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/periods")
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["name"] == "FilingPeriod2024"

    def test_unauthed_get_submissions(
        self, mocker: MockerFixture, app_fixture: FastAPI, get_filing_period_mock: Mock, unauthed_user_mock: Mock
    ):
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/123456790/filings/1/submissions")
        assert res.status_code == 403

    def test_get_filings(self, app_fixture: FastAPI, get_filings_mock: Mock):
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/FilingPeriod2024")
        get_filings_mock.assert_called_with(ANY, "FilingPeriod2024")
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["lei"] == "12345678"

    def test_get_filings_with_error(self, app_fixture: FastAPI, get_filings_error_mock: Mock):
        client = TestClient(app_fixture)
        response = client.get("/v1/filing/FilingPeriod2025")
        assert response.status_code == 500
        assert response.json() == {
            "detail": "There is no Filing Period with name FilingPeriod2025 defined in the database."
        }

    async def test_get_submissions(self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock):
        mock = mocker.patch("entities.repos.submission_repo.get_submissions")
        mock.return_value = [
            SubmissionDAO(
                submitter="test1@cfpb.gov",
                filing=1,
                state=SubmissionState.SUBMISSION_UPLOADED,
                validation_ruleset_version="v1",
                submission_time=datetime.datetime.now(),
            )
        ]

        client = TestClient(app_fixture)
        res = client.get("/v1/filing/123456790/filings/1/submissions")
        results = res.json()
        mock.assert_called_with(ANY, 1)
        assert res.status_code == 200
        assert len(results) == 1
        assert results[0]["submitter"] == "test1@cfpb.gov"
        assert results[0]["state"] == SubmissionState.SUBMISSION_UPLOADED

        # verify an empty submission list returns ok
        mock.return_value = []
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/123456790/filings/2/submissions")
        results = res.json()
        mock.assert_called_with(ANY, 2)
        assert res.status_code == 200
        assert len(results) == 0

    async def test_get_latest_submission(self, mocker: MockerFixture, app_fixture: FastAPI):
        mock = mocker.patch("entities.repos.submission_repo.get_latest_submission")
        mock.return_value = SubmissionDAO(
            submitter="test1@cfpb.gov",
            filing=1,
            state=SubmissionState.VALIDATION_IN_PROGRESS,
            validation_ruleset_version="v1",
            submission_time=datetime.datetime.now(),
        )

        client = TestClient(app_fixture)
        res = client.get("/v1/filing/123456790/filings/1/submissions/latest")
        result = res.json()
        mock.assert_called_with(ANY, 1)
        assert res.status_code == 200
        assert result["state"] == SubmissionState.VALIDATION_IN_PROGRESS

        # verify an empty submission result is ok
        mock.return_value = []
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/123456790/filings/1/submissions/latest")
        mock.assert_called_with(ANY, 1)
        assert res.status_code == 204
