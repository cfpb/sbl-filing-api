import asyncio
import datetime
from http import HTTPStatus
import httpx
import os
import pytest

from copy import deepcopy
from datetime import datetime as dt

from unittest.mock import ANY, Mock, AsyncMock

from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from sbl_filing_api.entities.models.dao import (
    SubmissionDAO,
    SubmissionState,
    FilingTaskState,
    ContactInfoDAO,
    FilingDAO,
    UserActionDAO,
)
from sbl_filing_api.entities.models.dto import ContactInfoDTO
from sbl_filing_api.entities.models.model_enums import UserActionType
from sbl_filing_api.routers.dependencies import verify_lei
from sbl_filing_api.services import submission_processor
from sbl_filing_api.services.multithread_handler import handle_submission, check_future

from sqlalchemy.exc import IntegrityError
from tempfile import NamedTemporaryFile
from sbl_filing_api.config import regex_configs


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
        res = client.get("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/")
        assert res.status_code == 403

    def test_get_filing(self, app_fixture: FastAPI, get_filing_mock: Mock, authed_user_mock: Mock):
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890ABCDEFGH00/filings/2024/")
        get_filing_mock.assert_called_with(ANY, "1234567890ABCDEFGH00", "2024")
        assert res.status_code == 200
        assert res.json()["lei"] == "1234567890ABCDEFGH00"
        assert res.json()["filing_period"] == "2024"

        get_filing_mock.return_value = None
        res = client.get("/v1/filing/institutions/1234567890ABCDEFGH00/filings/2024/")
        assert res.status_code == 204

    def test_unauthed_post_filing(self, app_fixture: FastAPI):
        client = TestClient(app_fixture)
        res = client.post("/v1/filing/institutions/ZXWVUTSRQP/filings/2024/")
        assert res.status_code == 403

    def test_post_filing(
        self,
        mocker: MockerFixture,
        app_fixture: FastAPI,
        get_filing_period_mock,
        post_filing_mock: Mock,
        authed_user_mock: Mock,
    ):
        client = TestClient(app_fixture)
        get_filing_period_by_code_mock = mocker.patch("sbl_filing_api.entities.repos.submission_repo.get_filing_period")

        # testing with a period that does not exist
        get_filing_period_by_code_mock.return_value = None
        res = client.post("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2025/")
        assert res.status_code == 404

        assert (
            res.json()["error_detail"]
            == "The period (2025) does not exist, therefore a Filing can not be created for this period."
        )

        get_filing_period_by_code_mock.return_value = get_filing_period_mock.return_value
        user_action_create = UserActionDAO(
            id=1,
            user_id="123456-7890-ABCDEF-GHIJ",
            user_name="Test Creator",
            user_email="test@local.host",
            action_type=UserActionType.CREATE,
            timestamp=datetime.datetime.now(),
        )
        mock_add_creator = mocker.patch("sbl_filing_api.entities.repos.submission_repo.add_user_action")
        mock_add_creator.side_effect = Exception("Error while trying to process CREATE User Action")
        res = client.post("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2025/")
        assert res.status_code == 500
        assert res.content == b'"Error while trying to process CREATE User Action"'

        mock_add_creator.return_value = user_action_create
        mock_add_creator.side_effect = None
        post_filing_mock.side_effect = IntegrityError(None, None, None)
        res = client.post("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/")
        assert res.status_code == 409
        assert res.json()["error_detail"] == "Filing already exists for Filing Period 2024 and LEI 1234567890ZXWVUTSR00"

        post_filing_mock.side_effect = None
        res = client.post("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/")
        post_filing_mock.assert_called_with(ANY, "1234567890ZXWVUTSR00", "2024", creator_id=1)
        assert res.status_code == 200
        assert res.json()["lei"] == "1234567890ZXWVUTSR00"
        assert res.json()["filing_period"] == "2024"

    def test_unauthed_get_submissions(
        self, mocker: MockerFixture, app_fixture: FastAPI, get_filing_period_mock: Mock, unauthed_user_mock: Mock
    ):
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/123456790/filings/2024/submissions")
        assert res.status_code == 403

    async def test_get_submissions(self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock):
        user_action_submit = UserActionDAO(
            id=2,
            user_id="123456-7890-ABCDEF-GHIJ",
            user_name="test submitter",
            user_email="test@local.host",
            action_type=UserActionType.SUBMIT,
            timestamp=datetime.datetime.now(),
        )
        mock = mocker.patch("sbl_filing_api.entities.repos.submission_repo.get_submissions")
        mock.return_value = [
            SubmissionDAO(
                filing=1,
                state=SubmissionState.SUBMISSION_UPLOADED,
                validation_ruleset_version="v1",
                submission_time=datetime.datetime.now(),
                filename="file1.csv",
                submitter_id=2,
                submitter=user_action_submit,
            )
        ]

        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions")
        results = res.json()
        mock.assert_called_with(ANY, "1234567890ZXWVUTSR00", "2024")
        assert res.status_code == 200
        assert len(results) == 1
        assert results[0]["state"] == SubmissionState.SUBMISSION_UPLOADED

        # verify an empty submission list returns ok
        mock.return_value = []
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions")
        results = res.json()
        mock.assert_called_with(ANY, "1234567890ZXWVUTSR00", "2024")
        assert res.status_code == 200
        assert len(results) == 0

    def test_unauthed_get_latest_submissions(
        self, mocker: MockerFixture, app_fixture: FastAPI, get_filing_period_mock: Mock
    ):
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/123456790/filings/2024/submissions/latest")
        assert res.status_code == 403

    async def test_get_latest_submission(self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock):
        user_action_submit = UserActionDAO(
            id=2,
            user_id="123456-7890-ABCDEF-GHIJ",
            user_name="test submitter",
            user_email="test@local.host",
            action_type=UserActionType.SUBMIT,
            timestamp=datetime.datetime.now(),
        )
        mock = mocker.patch("sbl_filing_api.entities.repos.submission_repo.get_latest_submission")
        mock.return_value = SubmissionDAO(
            filing=1,
            state=SubmissionState.VALIDATION_IN_PROGRESS,
            validation_ruleset_version="v1",
            submission_time=datetime.datetime.now(),
            filename="file1.csv",
            submitter_id=2,
            submitter=user_action_submit,
        )

        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions/latest")
        result = res.json()
        mock.assert_called_with(ANY, "1234567890ZXWVUTSR00", "2024")
        assert res.status_code == 200
        assert result["state"] == SubmissionState.VALIDATION_IN_PROGRESS

        # verify an empty submission result is ok
        mock.return_value = []
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions/latest")
        mock.assert_called_with(ANY, "1234567890ZXWVUTSR00", "2024")
        assert res.status_code == 204

    def test_unauthed_get_submission_by_id(self, mocker: MockerFixture, app_fixture: FastAPI):
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/123456790/filings/2024/submissions/1")
        assert res.status_code == 403

    async def test_get_submission_by_id(self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock):
        user_action_submit = UserActionDAO(
            id=2,
            user_id="123456-7890-ABCDEF-GHIJ",
            user_name="test submitter",
            user_email="test@local.host",
            action_type=UserActionType.SUBMIT,
            timestamp=datetime.datetime.now(),
        )
        mock = mocker.patch("sbl_filing_api.entities.repos.submission_repo.get_submission")
        mock.return_value = SubmissionDAO(
            id=1,
            filing=1,
            state=SubmissionState.VALIDATION_WITH_ERRORS,
            validation_ruleset_version="v1",
            submission_time=datetime.datetime.now(),
            filename="file1.csv",
            submitter_id=2,
            submitter=user_action_submit,
        )

        client = TestClient(app_fixture)

        res = client.get("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions/1")
        mock.assert_called_with(ANY, 1)
        assert res.status_code == 200

        mock.return_value = None
        res = client.get("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions/1")
        mock.assert_called_with(ANY, 1)
        assert res.status_code == 404

    def test_authed_upload_file(
        self,
        mocker: MockerFixture,
        app_fixture: FastAPI,
        authed_user_mock: Mock,
        submission_csv: str,
        get_filing_mock: Mock,
    ):
        user_action_submit = UserActionDAO(
            id=1,
            user_id="123456-7890-ABCDEF-GHIJ",
            user_name="test submitter",
            user_email="test@local.host",
            action_type=UserActionType.SUBMIT,
            timestamp=datetime.datetime.now(),
        )

        return_sub = SubmissionDAO(
            id=1,
            filing=1,
            state=SubmissionState.SUBMISSION_UPLOADED,
            filename="submission.csv",
            submitter_id=1,
            submitter=user_action_submit,
        )

        mock_validate_file = mocker.patch("sbl_filing_api.services.submission_processor.validate_file_processable")
        mock_validate_file.return_value = None

        mock_upload = mocker.patch("sbl_filing_api.services.submission_processor.upload_to_storage")
        mock_upload.return_value = None

        mock_get_loop = mocker.patch("asyncio.get_event_loop")
        mock_event_loop = Mock()
        mock_get_loop.return_value = mock_event_loop
        mock_event_loop.run_in_executor.return_value = asyncio.Future()

        mock_background_task = mocker.patch("fastapi.BackgroundTasks.add_task")

        async_mock = AsyncMock(return_value=return_sub)
        mock_add_submission = mocker.patch(
            "sbl_filing_api.entities.repos.submission_repo.add_submission", side_effect=async_mock
        )
        mock_update_submission = mocker.patch(
            "sbl_filing_api.entities.repos.submission_repo.update_submission", side_effect=async_mock
        )
        mock_add_submitter = mocker.patch("sbl_filing_api.entities.repos.submission_repo.add_user_action")
        mock_add_submitter.return_value = user_action_submit

        files = {"file": ("submission.csv", open(submission_csv, "rb"))}
        client = TestClient(app_fixture)

        res = client.post("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions", files=files)
        mock_add_submission.assert_called_with(ANY, 1, "submission.csv", user_action_submit.id)
        mock_event_loop.run_in_executor.assert_called_with(
            ANY, handle_submission, "2024", "1234567890ZXWVUTSR00", return_sub, open(submission_csv, "rb").read(), ANY
        )
        assert mock_event_loop.run_in_executor.call_args.args[6]["continue"]
        mock_background_task.assert_called_with(
            check_future, mock_event_loop.run_in_executor.return_value, return_sub.id, ANY
        )
        assert mock_background_task.call_args.args[3]["continue"]
        assert mock_update_submission.call_args.args[1].state == SubmissionState.SUBMISSION_UPLOADED
        assert res.status_code == 200
        assert res.json()["id"] == 1
        assert res.json()["state"] == SubmissionState.SUBMISSION_UPLOADED
        assert res.json()["submitter"]["id"] == 1
        assert res.json()["submitter"]["user_id"] == "123456-7890-ABCDEF-GHIJ"
        assert res.json()["submitter"]["user_name"] == "test submitter"
        assert res.json()["submitter"]["user_email"] == "test@local.host"
        assert res.json()["submitter"]["action_type"] == UserActionType.SUBMIT

        get_filing_mock.return_value = None
        res = client.post("/v1/filing/institutions/ABCDEFG/filings/2024/submissions", files=files)
        assert res.status_code == 404
        assert res.json()["error_detail"] == "There is no Filing for LEI ABCDEFG in period 2024, unable to submit file."

    def test_unauthed_upload_file(self, mocker: MockerFixture, app_fixture: FastAPI, submission_csv: str):
        files = {"file": ("submission.csv", open(submission_csv, "rb"))}
        client = TestClient(app_fixture)
        res = client.post("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions", files=files)
        assert res.status_code == 403

    def test_upload_file_invalid_type(
        self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock, submission_csv: str
    ):
        mock = mocker.patch("sbl_filing_api.services.submission_processor.validate_file_processable")
        mock.side_effect = HTTPException(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        client = TestClient(app_fixture)
        files = {"file": ("submission.csv", open(submission_csv, "rb"))}
        res = client.post("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions", files=files)
        assert res.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE

    def test_upload_file_invalid_size(
        self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock, submission_csv: str
    ):
        mock = mocker.patch("sbl_filing_api.services.submission_processor.validate_file_processable")
        mock.side_effect = HTTPException(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        client = TestClient(app_fixture)
        files = {"file": ("submission.csv", open(submission_csv, "rb"))}
        res = client.post("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions", files=files)
        assert res.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE

    def test_submission_update_fail(
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
            filename="submission.csv",
        )

        mock_validate_file = mocker.patch("sbl_filing_api.services.submission_processor.validate_file_processable")
        mock_validate_file.return_value = None

        async_mock = AsyncMock(return_value=return_sub)
        mocker.patch("sbl_filing_api.entities.repos.submission_repo.add_submission", side_effect=async_mock)

        mock_upload = mocker.patch("sbl_filing_api.services.submission_processor.upload_to_storage")
        mock_upload.return_value = None

        mock_update_submission = mocker.patch(
            "sbl_filing_api.entities.repos.submission_repo.update_submission", side_effect=async_mock
        )

        mock_add_submitter = mocker.patch("sbl_filing_api.entities.repos.submission_repo.add_user_action")
        mock_add_submitter.side_effect = RuntimeError("Failed to add submitter.")

        file = {"file": ("submission.csv", open(submission_csv, "rb"))}
        client = TestClient(app_fixture)

        res = client.post("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions", files=file)
        assert res.status_code == 500
        assert res.json()["error_detail"] == "Error while trying to process SUBMIT User Action"

        mock_add_submitter.side_effect = None
        mock_add_submitter.return_value = UserActionDAO(
            id=2,
            user_id="123456-7890-ABCDEF-GHIJ",
            user_name="test submitter",
            user_email="test@local.host",
            action_type=UserActionType.SUBMIT,
            timestamp=datetime.datetime.now(),
        )

        mock_upload.side_effect = HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Failed to upload file"
        )
        res = client.post("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions", files=file)
        assert mock_update_submission.call_args.args[1].state == SubmissionState.UPLOAD_FAILED
        assert res.status_code == 500
        assert res.json()["error_detail"] == "Error while trying to process SUBMIT User Action"

    def test_submission_second_update_fail(
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
            filename="submission.csv",
        )

        log_mock = mocker.patch("sbl_filing_api.routers.filing.logger.error")

        mock_validate_file = mocker.patch("sbl_filing_api.services.submission_processor.validate_file_processable")
        mock_validate_file.return_value = None

        async_mock = AsyncMock(return_value=return_sub)
        mocker.patch("sbl_filing_api.entities.repos.submission_repo.add_submission", side_effect=async_mock)

        mock_upload = mocker.patch("sbl_filing_api.services.submission_processor.upload_to_storage")
        mock_upload.return_value = None

        mocker.patch(
            "sbl_filing_api.entities.repos.submission_repo.update_submission",
            side_effect=Exception("Can't connect to database"),
        )

        mock_add_submitter = mocker.patch("sbl_filing_api.entities.repos.submission_repo.add_user_action")
        mock_add_submitter.side_effect = AsyncMock(
            return_value=UserActionDAO(
                id=2,
                user_id="123456-7890-ABCDEF-GHIJ",
                user_name="test submitter",
                user_email="test@local.host",
                action_type=UserActionType.SUBMIT,
                timestamp=datetime.datetime.now(),
            )
        )

        file = {"file": ("submission.csv", open(submission_csv, "rb"))}

        client = TestClient(app_fixture)

        res = client.post("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions", files=file)
        log_mock.assert_called_with(
            (
                f"Error updating submission 1 to {SubmissionState.UPLOAD_FAILED} state during error handling,"
                f" the submission may be stuck in the {SubmissionState.SUBMISSION_STARTED} or {SubmissionState.SUBMISSION_UPLOADED} state."
            ),
            ANY,
            exc_info=True,
            stack_info=True,
        )
        assert res.status_code == 500
        assert res.json()["error_detail"] == "Error while trying to process SUBMIT User Action"

    async def test_unauthed_patch_filing(self, app_fixture: FastAPI):
        client = TestClient(app_fixture)

        res = client.put(
            "/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2025/institution-snapshot-id",
            json={"institution_snapshot_id": "v3"},
        )
        assert res.status_code == 403

    async def test_patch_filing(
        self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock, get_filing_mock: Mock
    ):
        filing_return = get_filing_mock.return_value

        mock = mocker.patch("sbl_filing_api.entities.repos.submission_repo.upsert_filing")
        updated_filing_obj = deepcopy(get_filing_mock.return_value)
        updated_filing_obj.institution_snapshot_id = "v3"
        mock.return_value = updated_filing_obj

        client = TestClient(app_fixture)

        # no existing filing for endpoint
        get_filing_mock.return_value = None
        res = client.put(
            "/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2025/institution-snapshot-id",
            json={"institution_snapshot_id": "v3"},
        )
        assert res.status_code == 404
        assert (
            res.json()["error_detail"]
            == "A Filing for the LEI (1234567890ZXWVUTSR00) and period (2025) that was attempted to be updated does not exist."
        )

        # no known field for endpoint
        get_filing_mock.return_value = filing_return
        res = client.put(
            "/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/unknown_field",
            json={"institution_snapshot_id": "v3"},
        )
        assert res.status_code == 404

        # unallowed value data type
        res = client.put(
            "/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2025/institution-snapshot-id",
            json={"institution_snapshot_id": ["1", "2"]},
        )
        assert res.status_code == 422

        # good
        res = client.put(
            "/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2025/institution-snapshot-id",
            json={"institution_snapshot_id": "v3"},
        )
        assert res.status_code == 200
        assert res.json()["institution_snapshot_id"] == "v3"

        # no existing filing for contact_info
        get_filing_mock.return_value = None
        res = client.put(
            "/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/contact-info",
            json={
                "id": 1,
                "filing": 1,
                "first_name": "test_first_name_1",
                "last_name": "test_last_name_1",
                "hq_address_street_1": "address street 1",
                "hq_address_street_2": "",
                "hq_address_city": "Test City 1",
                "hq_address_state": "TS",
                "hq_address_zip": "12345",
                "phone_number": "112-345-6789",
                "email": "name_1@email.test",
            },
        )
        assert res.status_code == 404
        assert (
            res.json()["error_detail"]
            == "A Filing for the LEI (1234567890ZXWVUTSR00) and period (2024) that was attempted to be updated does not exist."
        )

    async def test_unauthed_task_update(self, app_fixture: FastAPI, unauthed_user_mock: Mock):
        client = TestClient(app_fixture)
        res = client.post(
            "/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/tasks/Task-1",
            json={"state": "COMPLETED"},
        )
        assert res.status_code == 403

    async def test_task_update(self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock):
        mock = mocker.patch("sbl_filing_api.entities.repos.submission_repo.update_task_state")
        client = TestClient(app_fixture)
        res = client.post(
            "/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/tasks/Task-1",
            json={"state": "COMPLETED"},
        )
        assert res.status_code == 200
        mock.assert_called_with(
            ANY, "1234567890ZXWVUTSR00", "2024", "Task-1", FilingTaskState.COMPLETED, authed_user_mock.return_value[1]
        )

    def test_unauthed_user_lei_association(
        self,
        mocker: MockerFixture,
        app_fixture: FastAPI,
        unauthed_user_mock: Mock,
        get_filing_mock: Mock,
        get_filing_period_mock: Mock,
    ):
        client = TestClient(app_fixture)

        res = client.get("/v1/filing/institutions/1234567890ABCDEFGH00/filings/2024/")
        assert res.status_code == 403

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

        res = client.get("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/")
        assert res.status_code == 403
        assert res.json()["error_detail"] == "LEI 1234567890ZXWVUTSR00 is not associated with the user."

        res = client.get("/v1/filing/institutions/1234567890ABCDEFGH00/filings/2024/")
        assert res.status_code == 200

    def test_verify_lei_dependency(self, mocker: MockerFixture):
        mock_user_fi_service = mocker.patch("sbl_filing_api.routers.dependencies.httpx.get")
        mock_user_fi_service.return_value = httpx.Response(200, json={"is_active": False})
        with pytest.raises(HTTPException) as http_exc:
            request = Request(scope={"type": "http", "headers": [(b"authorization", b"123")]})
            verify_lei(request=request, lei="1234567890ZXWVUTSR00")
        assert isinstance(http_exc.value, HTTPException)
        assert http_exc.value.status_code == 403
        assert http_exc.value.detail == "LEI 1234567890ZXWVUTSR00 is in an inactive state."

    async def test_unauthed_get_contact_info(self, app_fixture: FastAPI, unauthed_user_mock: Mock):
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/contact-info")
        assert res.status_code == 403

    async def test_get_contact_info(
        self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock, get_filing_mock
    ):
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/contact-info")
        result = res.json()

        assert res.status_code == 200
        assert result["id"] == 1
        assert result["first_name"] == "test_first_name_1"
        assert result["last_name"] == "test_last_name_1"
        assert result["hq_address_street_1"] == "address street 1"
        assert result["hq_address_street_2"] == "address street 2"
        assert result["hq_address_city"] == "Test City"
        assert result["hq_address_state"] == "TS"
        assert result["hq_address_zip"] == "12345"
        assert result["phone_number"] == "112-345-6789"
        assert result["email"] == "test1@cfpb.gov"

        # no contact_info for endpoint
        get_filing_mock.return_value = None
        res = client.get("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/contact-info")
        assert res.status_code == 404

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
            "phone_number": "112-345-6789",
            "email": "name_1@email.test",
        }
        client = TestClient(app_fixture)
        res = client.put(
            "/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/contact-info", json=contact_info_json
        )
        assert res.status_code == 403

    def test_put_contact_info(
        self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock, get_filing_mock: Mock
    ):
        get_filing_mock.return_value

        mock = mocker.patch("sbl_filing_api.entities.repos.submission_repo.update_contact_info")
        mock.return_value = FilingDAO(
            id=1,
            lei="1234567890ZXWVUTSR00",
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
                phone_number="112-345-6789",
                email="name_1@email.test",
            ),
            creator_id=1,
            creator=UserActionDAO(
                id=1,
                user_id="123456-7890-ABCDEF-GHIJ",
                user_name="test creator",
                user_email="test@local.host",
                action_type=UserActionType.CREATE,
                timestamp=datetime.datetime.now(),
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
            "phone_number": "112-345-6789",
            "email": "name_1@email.test",
        }

        res = client.put(
            "/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/contact-info", json=contact_info_json
        )

        assert res.status_code == 200

        result = res.json()
        assert result["id"] == 1
        assert result["lei"] == "1234567890ZXWVUTSR00"
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
        assert result["contact_info"]["phone_number"] == "112-345-6789"
        assert result["contact_info"]["email"] == "name_1@email.test"

        mock.assert_called_with(
            ANY,
            "1234567890ZXWVUTSR00",
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
                phone_number="112-345-6789",
            ),
        )

    async def test_accept_submission(self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock):
        user_action_submit = UserActionDAO(
            id=2,
            user_id="123456-7890-ABCDEF-GHIJ",
            user_name="test submitter",
            user_email="test@local.host",
            action_type=UserActionType.SUBMIT,
            timestamp=datetime.datetime.now(),
        )

        user_action_accept = UserActionDAO(
            id=3,
            user_id="1234-5678-ABCD-EFGH",
            user_name="test accepter",
            user_email="test@local.host",
            action_type=UserActionType.ACCEPT,
            timestamp=datetime.datetime.now(),
        )
        mock = mocker.patch("sbl_filing_api.entities.repos.submission_repo.get_submission")
        mock.return_value = SubmissionDAO(
            id=1,
            filing=1,
            state=SubmissionState.VALIDATION_WITH_ERRORS,
            validation_ruleset_version="v1",
            submission_time=datetime.datetime.now(),
            filename="file1.csv",
            submitter_id=2,
            submitter=user_action_submit,
        )

        update_accepter_mock = mocker.patch("sbl_filing_api.entities.repos.submission_repo.add_user_action")
        update_accepter_mock.return_value = user_action_accept

        update_mock = mocker.patch("sbl_filing_api.entities.repos.submission_repo.update_submission")
        update_mock.return_value = SubmissionDAO(
            id=1,
            filing=1,
            state=SubmissionState.SUBMISSION_ACCEPTED,
            validation_ruleset_version="v1",
            submission_time=datetime.datetime.now(),
            filename="file1.csv",
            submitter_id=2,
            submitter=user_action_submit,
            accepter_id=update_accepter_mock.return_value.id,
            accepter=update_accepter_mock.return_value,
        )

        client = TestClient(app_fixture)
        res = client.put("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions/1/accept")
        assert res.status_code == 403
        assert (
            res.json()["error_detail"]
            == "Submission 1 for LEI 1234567890ZXWVUTSR00 in filing period 2024 is not in an acceptable state.  Submissions must be validated successfully or with only warnings to be accepted."
        )

        mock.return_value.state = SubmissionState.VALIDATION_SUCCESSFUL
        res = client.put("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions/1/accept")
        update_mock.assert_called_once()
        update_accepter_mock.assert_called_once_with(
            ANY,
            user_id="123456-7890-ABCDEF-GHIJ",
            user_name="Test User",
            user_email="test@local.host",
            action_type=UserActionType.ACCEPT,
        )

        assert res.json()["state"] == "SUBMISSION_ACCEPTED"
        assert res.json()["id"] == 1
        assert res.json()["accepter"]["id"] == 3
        assert res.json()["accepter"]["user_id"] == "1234-5678-ABCD-EFGH"
        assert res.json()["accepter"]["user_name"] == "test accepter"
        assert res.json()["accepter"]["user_email"] == "test@local.host"
        assert res.json()["accepter"]["action_type"] == UserActionType.ACCEPT
        assert res.status_code == 200

        mock.return_value = None
        res = client.put("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions/1/accept")
        assert res.status_code == 404
        assert res.json()["error_detail"] == "Submission ID 1 does not exist, cannot accept a non-existing submission."

    async def test_good_sign_filing(
        self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock, get_filing_mock: Mock
    ):
        mock = mocker.patch("sbl_filing_api.entities.repos.submission_repo.get_latest_submission")
        mock.return_value = SubmissionDAO(
            id=1,
            submitter=UserActionDAO(
                id=1,
                user_id="123456-7890-ABCDEF-GHIJ",
                user_name="Test Submitter User",
                user_email="test1@cfpb.gov",
                action_type=UserActionType.SUBMIT,
                timestamp=datetime.datetime.now(),
            ),
            filing=1,
            state=SubmissionState.SUBMISSION_ACCEPTED,
            validation_ruleset_version="v1",
            submission_time=datetime.datetime.now(),
            filename="file1.csv",
        )

        add_sig_mock = mocker.patch("sbl_filing_api.entities.repos.submission_repo.add_user_action")
        add_sig_mock.return_value = UserActionDAO(
            id=2,
            user_id="123456-7890-ABCDEF-GHIJ",
            user_name="Test User",
            user_email="test@local.host",
            timestamp=datetime.datetime.now(),
            action_type=UserActionType.SIGN,
        )

        upsert_mock = mocker.patch("sbl_filing_api.entities.repos.submission_repo.upsert_filing")
        updated_filing_obj = deepcopy(get_filing_mock.return_value)
        upsert_mock.return_value = updated_filing_obj

        client = TestClient(app_fixture)
        res = client.put("/v1/filing/institutions/1234567890ABCDEFGH00/filings/2024/sign")
        add_sig_mock.assert_called_with(
            ANY,
            user_id="123456-7890-ABCDEF-GHIJ",
            user_name="Test User",
            user_email="test@local.host",
            action_type=UserActionType.SIGN,
        )
        assert upsert_mock.call_args.args[1].confirmation_id.startswith("1234567890ABCDEFGH00-2024-1-")
        assert res.status_code == 200
        assert float(upsert_mock.call_args.args[1].confirmation_id.split("-")[3]) == pytest.approx(
            dt.now().timestamp(), abs=1.5
        )

    async def test_errors_sign_filing(
        self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock, get_filing_mock: Mock
    ):
        sub_mock = mocker.patch("sbl_filing_api.entities.repos.submission_repo.get_latest_submission")
        sub_mock.return_value = SubmissionDAO(
            id=1,
            submitter=UserActionDAO(
                id=1,
                user_id="1234-5678-ABCD-EFGH",
                user_name="Test Submitter User",
                user_email="test1@cfpb.gov",
                action_type=UserActionType.SUBMIT,
                timestamp=datetime.datetime.now(),
            ),
            filing=1,
            state=SubmissionState.VALIDATION_SUCCESSFUL,
            validation_ruleset_version="v1",
            submission_time=datetime.datetime.now(),
            filename="file1.csv",
        )

        client = TestClient(app_fixture)
        res = client.put("/v1/filing/institutions/1234567890ABCDEFGH00/filings/2024/sign")
        assert res.status_code == 403
        assert (
            res.json()["error_detail"]
            == "Cannot sign filing. Filing for 1234567890ABCDEFGH00 for period 2024 does not have a latest submission the SUBMISSION_ACCEPTED state."
        )

        sub_mock.return_value = None
        res = client.put("/v1/filing/institutions/1234567890ABCDEFGH00/filings/2024/sign")
        assert res.status_code == 403
        assert (
            res.json()["error_detail"]
            == "Cannot sign filing. Filing for 1234567890ABCDEFGH00 for period 2024 does not have a latest submission the SUBMISSION_ACCEPTED state."
        )

        sub_mock.return_value = SubmissionDAO(
            id=1,
            submitter=UserActionDAO(
                id=1,
                user_id="1234-5678-ABCD-EFGH",
                user_name="Test Submitter User",
                user_email="test1@cfpb.gov",
                action_type=UserActionType.SUBMIT,
                timestamp=datetime.datetime.now(),
            ),
            filing=1,
            state=SubmissionState.SUBMISSION_ACCEPTED,
            validation_ruleset_version="v1",
            submission_time=datetime.datetime.now(),
            filename="file1.csv",
        )

        """
        get_filing_mock.return_value.institution_snapshot_id = None
        res = client.put("/v1/filing/institutions/1234567890ABCDEFGH00/filings/2024/sign")
        assert res.status_code == 403
        assert (
            res.json()
            == "Cannot sign filing. Filing for 1234567890ABCDEFGH00 for period 2024 does not have institution snapshot id defined."
        )
        """

        get_filing_mock.return_value.contact_info = None
        res = client.put("/v1/filing/institutions/1234567890ABCDEFGH00/filings/2024/sign")
        assert res.status_code == 403
        assert (
            res.json()["error_detail"]
            == "Cannot sign filing. Filing for 1234567890ABCDEFGH00 for period 2024 does not have contact info defined."
        )

        get_filing_mock.return_value = None
        res = client.put("/v1/filing/institutions/1234567890ABCDEFGH00/filings/2024/sign")
        assert res.status_code == 404
        assert (
            res.json()["error_detail"]
            == "There is no Filing for LEI 1234567890ABCDEFGH00 in period 2024, unable to sign a non-existent Filing."
        )

    async def test_get_latest_sub_report(self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock):
        sub_mock = mocker.patch("sbl_filing_api.entities.repos.submission_repo.get_latest_submission")
        sub_mock.return_value = SubmissionDAO(
            id=1,
            submitter=UserActionDAO(
                id=1,
                user_id="1234-5678-ABCD-EFGH",
                user_name="Test Submitter User",
                user_email="test1@cfpb.gov",
                action_type=UserActionType.SUBMIT,
                timestamp=datetime.datetime.now(),
            ),
            filing=1,
            state=SubmissionState.VALIDATION_IN_PROGRESS,
            validation_ruleset_version="v1",
            submission_time=datetime.datetime.now(),
            filename="file1.csv",
        )

        file_content = b"Test"
        temp_file = NamedTemporaryFile(delete=False, suffix=".csv")
        temp_file.write(file_content)
        temp_file.close()
        file_mock = mocker.patch("sbl_filing_api.services.submission_processor.get_from_storage")
        file_mock.return_value = temp_file.name

        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions/latest/report")
        sub_mock.assert_called_with(ANY, "1234567890ZXWVUTSR00", "2024")
        file_mock.assert_called_with("2024", "1234567890ZXWVUTSR00", "1" + submission_processor.REPORT_QUALIFIER)
        assert res.status_code == 200
        assert res.text == "Test"
        assert res.headers["content-type"] == "text/csv; charset=utf-8"
        assert res.headers["content-disposition"] == 'attachment; filename="1_validation_report.csv"'

        sub_mock.return_value = []
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions/latest/report")
        sub_mock.assert_called_with(ANY, "1234567890ZXWVUTSR00", "2024")
        assert res.status_code == 204

        os.unlink(temp_file.name)

    async def test_get_sub_report(self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock):
        sub_mock = mocker.patch("sbl_filing_api.entities.repos.submission_repo.get_submission")
        sub_mock.return_value = SubmissionDAO(
            id=2,
            submitter=UserActionDAO(
                id=1,
                user_id="1234-5678-ABCD-EFGH",
                user_name="Test Submitter User",
                user_email="test1@cfpb.gov",
                action_type=UserActionType.SUBMIT,
                timestamp=datetime.datetime.now(),
            ),
            filing=1,
            state=SubmissionState.VALIDATION_IN_PROGRESS,
            validation_ruleset_version="v1",
            submission_time=datetime.datetime.now(),
            filename="file1.csv",
        )

        file_content = b"Test"
        temp_file = NamedTemporaryFile(delete=False, suffix=".csv")
        temp_file.write(file_content)
        temp_file.close()
        file_mock = mocker.patch("sbl_filing_api.services.submission_processor.get_from_storage")
        file_mock.return_value = temp_file.name

        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions/2/report")
        sub_mock.assert_called_with(ANY, 2)
        file_mock.assert_called_with("2024", "1234567890ZXWVUTSR00", "2" + submission_processor.REPORT_QUALIFIER)
        assert res.status_code == 200
        assert res.text == "Test"
        assert res.headers["content-type"] == "text/csv; charset=utf-8"
        assert res.headers["content-disposition"] == 'attachment; filename="2_validation_report.csv"'

        sub_mock.return_value = []
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/submissions/1/report")
        sub_mock.assert_called_with(ANY, 1)
        assert res.status_code == 404

        os.unlink(temp_file.name)

    def test_contact_info_invalid_email(self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock):
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
            "phone_number": "112-345-6789",
            "email": "test_email",
        }

        res = client.put(
            "/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/contact-info", json=contact_info_json
        )
        assert f"Value error, Invalid email test_email. {regex_configs.email.error_text}" in res.json()["error_detail"]
        assert res.status_code == 422

    def test_contact_info_invalid_phone_number(
        self, mocker: MockerFixture, app_fixture: FastAPI, authed_user_mock: Mock
    ):
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
            "phone_number": "1123456789",
            "email": "test@cfpb.gov",
        }

        res = client.put(
            "/v1/filing/institutions/1234567890ZXWVUTSR00/filings/2024/contact-info", json=contact_info_json
        )
        assert (
            f"Value error, Invalid phone number 1123456789. {regex_configs.phone_number.error_text}"
            in res.json()["error_detail"]
        )
        assert res.status_code == 422
