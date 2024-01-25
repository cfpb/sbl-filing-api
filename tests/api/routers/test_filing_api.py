from unittest.mock import ANY

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from entities.models import SubmissionDAO, SubmissionState


class TestFilingApi:
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
        return mock
        
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/123456790/filings/1/submissions")
        results = res.json()
        mock.assert_called_once_with(ANY, 1)
        assert res.status_code == 200
        assert len(results) == 1
        assert results[0]["submitter"] == "test1@cfpb.gov"
        assert results[0]["state"] == SubmissionState.SUBMISSION_UPLOADED
        
        #verify an empty submission list returns ok
        mock.return_value = []
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/123456790/filings/2/submissions")
        results = res.json()
        mock.assert_called_once_with(ANY, 2)
        assert res.status_code == 200
        assert len(results) == 0