import datetime

from copy import deepcopy

from unittest.mock import ANY, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from entities.models import SubmissionDAO, SubmissionState, FilingTaskState


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
        assert res.json()[0]["code"] == "2024"

    def test_unauthed_get_filing(self, app_fixture: FastAPI, get_filing_mock: Mock):
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890/filings/2024/")
        assert res.status_code == 403

    def test_get_filing(self, app_fixture: FastAPI, get_filing_mock: Mock, authed_user_mock: Mock):
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890/filings/2024/")
        get_filing_mock.assert_called_with(ANY, "1234567890", "2024")
        assert res.status_code == 200
        assert res.json()["lei"] == "1234567890"
        assert res.json()["filing_period"] == "2024"

        get_filing_mock.return_value = None
        res = client.get("/v1/filing/institutions/1234567890/filings/2024/")
        assert res.status_code == 204

    def test_unauthed_post_filing(self, app_fixture: FastAPI, post_filing_mock: Mock):
        client = TestClient(app_fixture)
        res = client.post("/v1/filing/institutions/ZXWVUTSRQP/filings/2024/")
        assert res.status_code == 403

    def test_post_filing(self, app_fixture: FastAPI, post_filing_mock: Mock, authed_user_mock: Mock):
        client = TestClient(app_fixture)
        res = client.post("/v1/filing/institutions/ZXWVUTSRQP/filings/2024/")
        post_filing_mock.assert_called_with(ANY, "ZXWVUTSRQP", "2024")
        assert res.status_code == 200
        assert res.json()["lei"] == "ZXWVUTSRQP"
        assert res.json()["filing_period"] == "2024"

    def test_unauthed_get_submissions(
        self, mocker: MockerFixture, app_fixture: FastAPI, get_filing_period_mock: Mock, unauthed_user_mock: Mock
    ):
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/123456790/filings/2024/submissions")
        assert res.status_code == 403

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
        res = client.get("/v1/filing/institutions/1234567890/filings/2024/submissions")
        results = res.json()
        mock.assert_called_with(ANY, "1234567890", "2024")
        assert res.status_code == 200
        assert len(results) == 1
        assert results[0]["submitter"] == "test1@cfpb.gov"
        assert results[0]["state"] == SubmissionState.SUBMISSION_UPLOADED

        # verify an empty submission list returns ok
        mock.return_value = []
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890/filings/2024/submissions")
        results = res.json()
        mock.assert_called_with(ANY, "1234567890", "2024")
        assert res.status_code == 200
        assert len(results) == 0

    def test_unauthed_get_latest_submissions(
        self, mocker: MockerFixture, app_fixture: FastAPI, get_filing_period_mock: Mock
    ):
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/123456790/filings/2024/submissions/latest")
        assert res.status_code == 403

    async def test_get_latest_submission(self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock):
        mock = mocker.patch("entities.repos.submission_repo.get_latest_submission")
        mock.return_value = SubmissionDAO(
            submitter="test1@cfpb.gov",
            filing=1,
            state=SubmissionState.VALIDATION_IN_PROGRESS,
            validation_ruleset_version="v1",
            submission_time=datetime.datetime.now(),
        )

        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890/filings/2024/submissions/latest")
        result = res.json()
        mock.assert_called_with(ANY, "1234567890", "2024")
        assert res.status_code == 200
        assert result["state"] == SubmissionState.VALIDATION_IN_PROGRESS

        # verify an empty submission result is ok
        mock.return_value = []
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890/filings/2024/submissions/latest")
        mock.assert_called_with(ANY, "1234567890", "2024")
        assert res.status_code == 204

    def test_authed_upload_file(
        self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock, submission_csv: str
    ):
        mock_upload = mocker.patch("services.submission_processor.upload_to_storage")
        mock_upload.return_value = None
        mock_validate_submission = mocker.patch("services.submission_processor.validate_submission")
        mock_validate_submission.return_value = None
        files = {"file": ("submission.csv", open(submission_csv, "rb"))}
        client = TestClient(app_fixture)
        res = client.post("/v1/filing/123456790/submissions/1", files=files)
        assert res.status_code == 202

    def test_unauthed_upload_file(self, mocker: MockerFixture, app_fixture: FastAPI, submission_csv: str):
        files = {"file": ("submission.csv", open(submission_csv, "rb"))}
        client = TestClient(app_fixture)
        res = client.post("/v1/filing/123456790/submissions/1", files=files)
        assert res.status_code == 403

    async def test_unauthed_patch_filing(self, app_fixture: FastAPI):
        client = TestClient(app_fixture)

        res = client.patch(
            "/v1/filing/institutions/1234567890/filings/2025/fields/institution_snapshot_id", json={"value": "v3"}
        )
        assert res.status_code == 403

    async def test_patch_filing(
        self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock, get_filing_mock: Mock
    ):
        filing_return = get_filing_mock.return_value

        mock = mocker.patch("entities.repos.submission_repo.upsert_filing")
        updated_filing_obj = deepcopy(get_filing_mock.return_value)
        updated_filing_obj.institution_snapshot_id = "v3"
        mock.return_value = updated_filing_obj

        client = TestClient(app_fixture)

        # no existing filing for endpoint
        get_filing_mock.return_value = None
        res = client.patch(
            "/v1/filing/institutions/1234567890/filings/2025/fields/institution_snapshot_id", json={"value": "v3"}
        )
        assert res.status_code == 204

        # no known field for endpoint
        get_filing_mock.return_value = filing_return
        res = client.patch("/v1/filing/institutions/1234567890/filings/2024/fields/unknown_field", json={"value": "v3"})
        assert res.status_code == 204

        # unallowed value data type
        res = client.patch(
            "/v1/filing/institutions/1234567890/filings/2025/fields/institution_snapshot_id", json={"value": ["1", "2"]}
        )
        assert res.status_code == 422

        # good
        res = client.patch(
            "/v1/filing/institutions/1234567890/filings/2025/fields/institution_snapshot_id", json={"value": "v3"}
        )
        assert res.status_code == 200
        assert res.json()["institution_snapshot_id"] == "v3"

    async def test_unauthed_task_update(self, app_fixture: FastAPI, unauthed_user_mock: Mock):
        client = TestClient(app_fixture)
        res = client.post(
            "/v1/filing/institutions/1234567890/filings/2024/tasks/Task-1",
            json={"state": "COMPLETED"},
        )
        assert res.status_code == 403

    async def test_task_update(self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock):
        mock = mocker.patch("entities.repos.submission_repo.update_task_state")
        client = TestClient(app_fixture)
        res = client.post(
            "/v1/filing/institutions/1234567890/filings/2024/tasks/Task-1",
            json={"state": "COMPLETED"},
        )
        assert res.status_code == 200
        mock.assert_called_with(
            ANY, "1234567890", "2024", "Task-1", FilingTaskState.COMPLETED, authed_user_mock.return_value[1]
        )
