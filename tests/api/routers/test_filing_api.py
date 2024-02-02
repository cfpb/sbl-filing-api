from unittest.mock import ANY, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from entities.models import SubmissionDAO, SubmissionState


class TestFilingApi:
    def test_get_periods(self, mocker: MockerFixture, app_fixture: FastAPI, get_filing_period_mock: Mock):
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/periods")
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["name"] == "FilingPeriod2024"

    async def test_get_submissions(self, mocker: MockerFixture, app_fixture: FastAPI):
        mock = mocker.patch("entities.repos.submission_repo.get_submissions")
        mock.return_value = [
            SubmissionDAO(
                submitter="test1@cfpb.gov",
                filing=1,
                state=SubmissionState.SUBMISSION_UPLOADED,
                validation_ruleset_version="v1",
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
