import datetime
from http import HTTPStatus
import httpx
import os
import pytest

from copy import deepcopy

from unittest.mock import ANY, Mock, AsyncMock

from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from entities.models import SubmissionDAO, SubmissionState, FilingTaskState, ContactInfoDAO, ContactInfoDTO, FilingDAO

from routers.dependencies import verify_lei

from sqlalchemy.exc import IntegrityError


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

    def test_unauthed_post_filing(self, app_fixture: FastAPI):
        client = TestClient(app_fixture)
        res = client.post("/v1/filing/institutions/ZXWVUTSRQP/filings/2024/")
        assert res.status_code == 403

    def test_post_filing(self, app_fixture: FastAPI, post_filing_mock: Mock, authed_user_mock: Mock):
        client = TestClient(app_fixture)
        post_filing_mock.side_effect = IntegrityError(None, None, None)
        res = client.post("/v1/filing/institutions/1234567890/filings/2024/")
        assert res.status_code == 409
        assert res.json()["detail"] == "Filing already exists for Filing Period 2024 and LEI 1234567890"

        post_filing_mock.side_effect = None
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
                filename="file1.csv",
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
            filename="file1.csv",
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

    def test_unauthed_get_submission_by_id(self, mocker: MockerFixture, app_fixture: FastAPI):
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/123456790/filings/2024/submissions/1")
        assert res.status_code == 403

    async def test_get_submission_by_id(self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock):
        mock = mocker.patch("entities.repos.submission_repo.get_submission")
        mock.return_value = SubmissionDAO(
            id=1,
            submitter="test1@cfpb.gov",
            filing=1,
            state=SubmissionState.VALIDATION_WITH_ERRORS,
            validation_ruleset_version="v1",
            submission_time=datetime.datetime.now(),
            filename="file1.csv",
        )

        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890/filings/2024/submissions/1")
        mock.assert_called_with(ANY, 1)
        assert res.status_code == 200

        mock.return_value = None
        res = client.get("/v1/filing/institutions/1234567890/filings/2024/submissions/1")
        mock.assert_called_with(ANY, 1)
        assert res.status_code == 204

    def test_authed_upload_file(
        self,
        mocker: MockerFixture,
        app_fixture: FastAPI,
        authed_user_mock: Mock,
        submission_csv: str,
        get_filing_mock: Mock,
    ):
        return_sub = SubmissionDAO(
            id=1,
            filing=1,
            state=SubmissionState.SUBMISSION_UPLOADED,
            submitter="123456-7890-ABCDEF-GHIJ",
            filename="submission.csv",
        )

        mock_validate_file = mocker.patch("services.submission_processor.validate_file_processable")
        mock_validate_file.return_value = None
        mock_upload = mocker.patch("services.submission_processor.upload_to_storage")
        mock_upload.return_value = None
        mock_validate_submission = mocker.patch("services.submission_processor.validate_and_update_submission")
        mock_validate_submission.return_value = None
        async_mock = AsyncMock(return_value=return_sub)
        mock_add_submission = mocker.patch("entities.repos.submission_repo.add_submission", side_effect=async_mock)
        mock_update_submission = mocker.patch(
            "entities.repos.submission_repo.update_submission", side_effect=async_mock
        )

        files = {"file": ("submission.csv", open(submission_csv, "rb"))}
        client = TestClient(app_fixture)

        res = client.post("/v1/filing/institutions/1234567890/filings/2024/submissions", files=files)
        mock_add_submission.assert_called_with(ANY, 1, "123456-7890-ABCDEF-GHIJ", "submission.csv")
        assert mock_update_submission.call_args.args[0].state == SubmissionState.SUBMISSION_UPLOADED
        assert res.status_code == 200
        assert res.json()["id"] == 1
        assert res.json()["state"] == SubmissionState.SUBMISSION_UPLOADED
        assert res.json()["submitter"] == "123456-7890-ABCDEF-GHIJ"

        get_filing_mock.return_value = None
        res = client.post("/v1/filing/institutions/ABCDEFG/filings/2024/submissions", files=files)
        assert res.status_code == 422
        assert res.json() == "There is no Filing for LEI ABCDEFG in period 2024, unable to submit file."

    def test_unauthed_upload_file(self, mocker: MockerFixture, app_fixture: FastAPI, submission_csv: str):
        files = {"file": ("submission.csv", open(submission_csv, "rb"))}
        client = TestClient(app_fixture)
        res = client.post("/v1/filing/institutions/1234567890/filings/2024/submissions", files=files)
        assert res.status_code == 403

    def test_upload_file_invalid_type(
        self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock, submission_csv: str
    ):
        mock = mocker.patch("services.submission_processor.validate_file_processable")
        mock.side_effect = HTTPException(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        client = TestClient(app_fixture)
        files = {"file": ("submission.csv", open(submission_csv, "rb"))}
        res = client.post("/v1/filing/institutions/1234567890/filings/2024/submissions", files=files)
        assert res.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE

    def test_upload_file_invalid_size(
        self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock, submission_csv: str
    ):
        mock = mocker.patch("services.submission_processor.validate_file_processable")
        mock.side_effect = HTTPException(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        client = TestClient(app_fixture)
        files = {"file": ("submission.csv", open(submission_csv, "rb"))}
        res = client.post("/v1/filing/institutions/1234567890/filings/2024/submissions", files=files)
        assert res.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE

    async def test_unauthed_patch_filing(self, app_fixture: FastAPI):
        client = TestClient(app_fixture)

        res = client.put(
            "/v1/filing/institutions/1234567890/filings/2025/institution-snapshot-id",
            json={"institution_snapshot_id": "v3"},
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
        res = client.put(
            "/v1/filing/institutions/1234567890/filings/2025/institution-snapshot-id",
            json={"institution_snapshot_id": "v3"},
        )
        assert res.status_code == 204

        # no known field for endpoint
        get_filing_mock.return_value = filing_return
        res = client.put(
            "/v1/filing/institutions/1234567890/filings/2024/unknown_field", json={"institution_snapshot_id": "v3"}
        )
        assert res.status_code == 404

        # unallowed value data type
        res = client.put(
            "/v1/filing/institutions/1234567890/filings/2025/institution-snapshot-id",
            json={"institution_snapshot_id": ["1", "2"]},
        )
        assert res.status_code == 422

        # good
        res = client.put(
            "/v1/filing/institutions/1234567890/filings/2025/institution-snapshot-id",
            json={"institution_snapshot_id": "v3"},
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

    def test_user_lei_association(
        self,
        mocker: MockerFixture,
        app_fixture: FastAPI,
        authed_user_mock: Mock,
        get_filing_mock: Mock,
        get_filing_period_mock: Mock,
    ):
        mocker.patch.dict(os.environ, {"ENV": "TEST"})
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/periods")
        assert res.status_code == 200

        res = client.get("/v1/filing/institutions/1234567890/filings/2024/")
        assert res.status_code == 403
        assert res.json()["detail"] == "LEI 1234567890 is not associated with the user."

        res = client.get("/v1/filing/institutions/123456ABCDEF/filings/2024/")
        assert res.status_code == 200

    def test_verify_lei_dependency(self, mocker: MockerFixture):
        mock_user_fi_service = mocker.patch("routers.dependencies.httpx.get")
        mock_user_fi_service.return_value = httpx.Response(200, json={"is_active": False})
        with pytest.raises(HTTPException) as http_exc:
            request = Request(scope={"type": "http", "headers": [(b"authorization", b"123")]})
            verify_lei(request=request, lei="1234567890")
        assert isinstance(http_exc.value, HTTPException)
        assert http_exc.value.status_code == 403
        assert http_exc.value.detail == "LEI 1234567890 is in an inactive state."

    async def test_unauthed_get_contact_info(self, app_fixture: FastAPI, unauthed_user_mock: Mock):
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890/filings/2024/contact-info")
        assert res.status_code == 403

    async def test_get_contact_info(self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock):
        mock = mocker.patch("entities.repos.submission_repo.get_contact_info")
        mock.return_value = ContactInfoDAO(
            id=1,
            filing=1,
            first_name="test_first_name_1",
            last_name="test_last_name_1",
            hq_address_street_1="address street 1",
            hq_address_street_2="",
            hq_address_city="Test City",
            hq_address_state="TS",
            hq_address_zip="12345",
            phone="112-345-6789",
            email="name_1@email.test",
        )

        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890/filings/2024/contact-info")
        result = res.json()

        assert res.status_code == 200
        assert result["id"] == 1
        assert result["first_name"] == "test_first_name_1"
        assert result["last_name"] == "test_last_name_1"
        assert result["hq_address_street_1"] == "address street 1"
        assert result["hq_address_street_2"] == ""
        assert result["hq_address_city"] == "Test City"
        assert result["hq_address_state"] == "TS"
        assert result["hq_address_zip"] == "12345"
        assert result["phone"] == "112-345-6789"
        assert result["email"] == "name_1@email.test"

        # no contact_info for endpoint
        mock.return_value = None
        res = client.get("/v1/filing/institutions/1234567890/filings/2024/contact-info")
        assert res.status_code == 204

    async def test_unauthed_put_contact_info(self, mocker: MockerFixture, app_fixture: FastAPI, unauthed_user_mock):
        contact_info_json = {
            "id": 1,
            "filing": 1,
            "first_name": "test_first_name_1",
            "last_name": "test_last_name_1",
            "hq_address_street_1": "address street 1",
            "hq_address_street_2": "",
            "hq_address_city": "Test City 1",
            "hq_address_state": "TS",
            "hq_address_zip": "12345",
            "phone": "112-345-6789",
            "email": "name_1@email.test",
        }
        client = TestClient(app_fixture)
        res = client.put("/v1/filing/institutions/1234567890/filings/2024/contact-info", json=contact_info_json)
        assert res.status_code == 403

    def test_put_contact_info(self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock):
        mock = mocker.patch("entities.repos.submission_repo.update_contact_info")
        mock.return_value = FilingDAO(
            id=1,
            lei="1234567890",
            institution_snapshot_id="Snapshot-1",
            filing_period="2024",
            contact_info=ContactInfoDAO(
                id=1,
                filing=1,
                first_name="test_first_name_1",
                last_name="test_last_name_1",
                hq_address_street_1="address street 1",
                hq_address_street_2="",
                hq_address_city="Test City 1",
                hq_address_state="TS",
                hq_address_zip="12345",
                phone="112-345-6789",
                email="name_1@email.test",
            ),
        )

        client = TestClient(app_fixture)
        contact_info_json = {
            "id": 1,
            "filing": 1,
            "first_name": "test_first_name_1",
            "last_name": "test_last_name_1",
            "hq_address_street_1": "address street 1",
            "hq_address_street_2": "",
            "hq_address_city": "Test City 1",
            "hq_address_state": "TS",
            "hq_address_zip": "12345",
            "phone": "112-345-6789",
            "email": "name_1@email.test",
        }
        res = client.put("/v1/filing/institutions/1234567890/filings/2024/contact-info", json=contact_info_json)

        assert res.status_code == 200

        result = res.json()
        assert result["id"] == 1
        assert result["lei"] == "1234567890"
        assert result["institution_snapshot_id"] == "Snapshot-1"
        assert result["filing_period"] == "2024"
        assert result["contact_info"]["id"] == 1
        assert result["contact_info"]["first_name"] == "test_first_name_1"
        assert result["contact_info"]["last_name"] == "test_last_name_1"
        assert result["contact_info"]["hq_address_street_1"] == "address street 1"
        assert result["contact_info"]["hq_address_street_2"] == ""
        assert result["contact_info"]["hq_address_city"] == "Test City 1"
        assert result["contact_info"]["hq_address_state"] == "TS"
        assert result["contact_info"]["hq_address_zip"] == "12345"
        assert result["contact_info"]["phone"] == "112-345-6789"
        assert result["contact_info"]["email"] == "name_1@email.test"

        mock.assert_called_with(
            ANY,
            "1234567890",
            "2024",
            ContactInfoDTO(
                id=1,
                first_name="test_first_name_1",
                last_name="test_last_name_1",
                hq_address_street_1="address street 1",
                hq_address_street_2="",
                hq_address_city="Test City 1",
                hq_address_state="TS",
                hq_address_zip="12345",
                email="name_1@email.test",
                phone="112-345-6789",
            ),
        )

    async def test_certify_submission(self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock):
        mock = mocker.patch("entities.repos.submission_repo.get_submission")
        mock.return_value = SubmissionDAO(
            id=1,
            submitter="test1@cfpb.gov",
            filing=1,
            state=SubmissionState.VALIDATION_WITH_ERRORS,
            validation_ruleset_version="v1",
            submission_time=datetime.datetime.now(),
            filename="file1.csv",
        )
        update_mock = mocker.patch("entities.repos.submission_repo.update_submission")
        update_mock.return_value = SubmissionDAO(
            id=1,
            submitter="test1@cfpb.gov",
            filing=1,
            state=SubmissionState.SUBMISSION_CERTIFIED,
            validation_ruleset_version="v1",
            submission_time=datetime.datetime.now(),
            filename="file1.csv",
        )
        client = TestClient(app_fixture)
        res = client.put("/v1/filing/institutions/1234567890/filings/2024/submissions/1/certify")
        assert res.status_code == 403
        assert (
            res.json()
            == "Submission 1 for LEI 1234567890 in filing period 2024 is not in a certifiable state.  Submissions must be validated successfully or with only warnings to be signed"
        )

        mock.return_value.state = SubmissionState.VALIDATION_SUCCESSFUL
        res = client.put("/v1/filing/institutions/1234567890/filings/2024/submissions/1/certify")
        update_mock.assert_called_once()
        assert update_mock.call_args.args[0].state == "SUBMISSION_CERTIFIED"
        assert update_mock.call_args.args[0].certifier == "123456-7890-ABCDEF-GHIJ"
        assert res.status_code == 200

        mock.return_value = None
        res = client.put("/v1/filing/institutions/1234567890/filings/2024/submissions/1/certify")
        assert res.status_code == 422
        assert res.json() == "Submission ID 1 does not exist, cannot certify a non-existing submission."
