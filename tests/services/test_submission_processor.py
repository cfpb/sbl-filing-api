import pandas as pd
import pytest

from http import HTTPStatus
from sbl_filing_api.services import submission_processor
from fastapi import HTTPException
from unittest.mock import Mock, ANY
from pytest_mock import MockerFixture
from sbl_filing_api.config import FsProtocol, settings
from sbl_filing_api.entities.models.dao import SubmissionDAO, SubmissionState
from regtech_data_validator.create_schemas import ValidationPhase
from regtech_data_validator.checks import Severity
from regtech_api_commons.api.exceptions import RegTechHttpException


class TestSubmissionProcessor:
    @pytest.fixture
    def mock_fs(self, mocker: MockerFixture) -> Mock:
        fs_mock_patch = mocker.patch("sbl_filing_api.services.submission_processor.AbstractFileSystem")
        return fs_mock_patch.return_value

    @pytest.fixture
    def mock_fs_func(self, mocker: MockerFixture, mock_fs: Mock) -> Mock:
        fs_func_mock = mocker.patch("sbl_filing_api.services.submission_processor.filesystem")
        fs_func_mock.return_value = mock_fs
        return fs_func_mock

    @pytest.fixture
    def mock_upload_file(self, mocker: MockerFixture) -> Mock:
        file_mock = mocker.patch("fastapi.UploadFile")
        return file_mock.return_value

    async def test_upload(self, mocker: MockerFixture, mock_fs_func: Mock, mock_fs: Mock):
        with mocker.mock_open(mock_fs.open):
            await submission_processor.upload_to_storage("test_period", "test", "test", b"test content local")
        mock_fs_func.assert_called()
        mock_fs.mkdirs.assert_called()
        mock_fs.open.assert_called_with("../upload/upload/test_period/test/test.csv", "wb")
        file_handle = mock_fs.open()
        file_handle.write.assert_called_with(b"test content local")

    async def test_read_from_storage(self, mocker: MockerFixture, mock_fs_func: Mock, mock_fs: Mock):
        await submission_processor.get_from_storage("2024", "1234567890", "1_report")
        mock_fs_func.assert_called_with(**settings.fs_download_config.__dict__)
        mock_fs.open.assert_called_with("../upload/upload/2024/1234567890/1_report.csv", "r")

    async def test_upload_s3(self, mocker: MockerFixture):
        default_fs_proto = settings.fs_upload_config.protocol
        settings.fs_upload_config.protocol = FsProtocol.S3.value

        boto3_mock = mocker.patch("sbl_filing_api.services.submission_processor.boto3.client")
        log_mock = mocker.patch("sbl_filing_api.services.submission_processor.log")
        s3_mock = Mock(["put_object"])
        s3_mock.put_object.return_value = {"test": "response"}
        boto3_mock.return_value = s3_mock

        await submission_processor.upload_to_storage("test_period", "test", "test", b"test content s3")

        boto3_mock.assert_called_with("s3")
        s3_mock.put_object.assert_called_with(
            Bucket=settings.fs_upload_config.root, Key="upload/test_period/test/test.csv", Body=b"test content s3"
        )
        log_mock.debug.assert_called_with(
            "s3 upload response for lei: %s, period: %s file: %s, response: %s",
            "test",
            "test_period",
            "test",
            {"test": "response"},
        )

        settings.fs_upload_config.protocol = default_fs_proto

    async def test_upload_failure(self, mocker: MockerFixture, mock_fs_func: Mock, mock_fs: Mock):
        mock_fs.mkdirs.side_effect = IOError("test")
        with pytest.raises(Exception) as e:
            await submission_processor.upload_to_storage("test_period", "test", "test", b"test content")
        assert isinstance(e.value, RegTechHttpException)
        assert e.value.name == "Upload Failure"

    async def test_read_failure(self, mocker: MockerFixture, mock_fs_func: Mock, mock_fs: Mock):
        mock_fs.open.side_effect = IOError("test")
        with pytest.raises(Exception) as e:
            await submission_processor.get_from_storage("2024", "1234567890", "1_report")
        assert isinstance(e.value, RegTechHttpException)
        assert e.value.name == "Download Failure"

    def test_validate_file_supported(self, mock_upload_file: Mock):
        mock_upload_file.filename = "test.csv"
        mock_upload_file.content_type = "text/csv"
        mock_upload_file.size = settings.submission_file_size - 1
        submission_processor.validate_file_processable(mock_upload_file)

    def test_file_not_supported_invalid_extension(self, mock_upload_file: Mock):
        mock_upload_file.filename = "test.txt"
        mock_upload_file.content_type = "text/csv"
        mock_upload_file.size = settings.submission_file_size - 1
        with pytest.raises(HTTPException) as e:
            submission_processor.validate_file_processable(mock_upload_file)
        assert e.value.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE

    def test_file_not_supported_invalid_content_type(self, mock_upload_file: Mock):
        mock_upload_file.filename = "test.csv"
        mock_upload_file.content_type = "text/plain"
        mock_upload_file.size = settings.submission_file_size - 1
        with pytest.raises(HTTPException) as e:
            submission_processor.validate_file_processable(mock_upload_file)
        assert e.value.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE

    def test_file_not_supported_file_size_too_large(self, mock_upload_file: Mock):
        mock_upload_file.filename = "test.csv"
        mock_upload_file.content_type = "text/csv"
        mock_upload_file.size = settings.submission_file_size + 1
        with pytest.raises(HTTPException) as e:
            submission_processor.validate_file_processable(mock_upload_file)
        assert e.value.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE

    async def test_validate_and_update_successful(
        self,
        mocker: MockerFixture,
        successful_submission_mock: Mock,
        build_validation_results_mock: Mock,
        df_to_download_mock: Mock,
    ):
        mock_sub = SubmissionDAO(
            id=1,
            filing=1,
            state=SubmissionState.SUBMISSION_UPLOADED,
            filename="submission.csv",
        )
        file_mock = mocker.patch("sbl_filing_api.services.submission_processor.upload_to_storage")
        df_to_download_mock.return_value = ""

        await submission_processor.validate_and_update_submission(
            "2024", "123456790", mock_sub, None, {"continue": True}
        )
        encoded_results = df_to_download_mock.return_value.encode("utf-8")
        assert file_mock.mock_calls[0].args == (
            "2024",
            "123456790",
            "1" + submission_processor.REPORT_QUALIFIER,
            encoded_results,
        )
        assert successful_submission_mock.mock_calls[0].args[1].state == SubmissionState.VALIDATION_IN_PROGRESS
        assert successful_submission_mock.mock_calls[0].args[1].validation_ruleset_version == "0.1.0"
        assert successful_submission_mock.mock_calls[1].args[1].state == "VALIDATION_SUCCESSFUL"

    async def test_validate_and_update_warnings(
        self,
        mocker: MockerFixture,
        warning_submission_mock: Mock,
        build_validation_results_mock: Mock,
        df_to_download_mock: Mock,
    ):
        mock_sub = SubmissionDAO(
            id=1,
            filing=1,
            state=SubmissionState.SUBMISSION_UPLOADED,
            filename="submission.csv",
        )
        file_mock = mocker.patch("sbl_filing_api.services.submission_processor.upload_to_storage")

        await submission_processor.validate_and_update_submission(
            "2024", "123456790", mock_sub, None, {"continue": True}
        )
        encoded_results = df_to_download_mock.return_value.encode("utf-8")
        assert file_mock.mock_calls[0].args == (
            "2024",
            "123456790",
            "1" + submission_processor.REPORT_QUALIFIER,
            encoded_results,
        )
        assert warning_submission_mock.mock_calls[0].args[1].state == SubmissionState.VALIDATION_IN_PROGRESS
        assert warning_submission_mock.mock_calls[0].args[1].validation_ruleset_version == "0.1.0"
        assert warning_submission_mock.mock_calls[1].args[1].state == "VALIDATION_WITH_WARNINGS"

    async def test_validate_and_update_errors(
        self,
        mocker: MockerFixture,
        error_submission_mock: Mock,
        build_validation_results_mock: Mock,
        df_to_download_mock: Mock,
    ):
        mock_sub = SubmissionDAO(
            id=1,
            filing=1,
            state=SubmissionState.SUBMISSION_UPLOADED,
            filename="submission.csv",
        )

        file_mock = mocker.patch("sbl_filing_api.services.submission_processor.upload_to_storage")

        await submission_processor.validate_and_update_submission(
            "2024", "123456790", mock_sub, None, {"continue": True}
        )
        encoded_results = df_to_download_mock.return_value.encode("utf-8")
        assert file_mock.mock_calls[0].args == (
            "2024",
            "123456790",
            "1" + submission_processor.REPORT_QUALIFIER,
            encoded_results,
        )
        assert error_submission_mock.mock_calls[0].args[1].state == SubmissionState.VALIDATION_IN_PROGRESS
        assert error_submission_mock.mock_calls[0].args[1].validation_ruleset_version == "0.1.0"
        assert error_submission_mock.mock_calls[1].args[1].state == "VALIDATION_WITH_ERRORS"

    async def test_validate_and_update_submission_malformed(
        self,
        mocker: MockerFixture,
    ):
        log_mock = mocker.patch("sbl_filing_api.services.submission_processor.log")

        mock_sub = SubmissionDAO(
            id=1,
            filing=1,
            state=SubmissionState.SUBMISSION_UPLOADED,
            filename="submission.csv",
        )

        mock_update_submission = mocker.patch("sbl_filing_api.services.submission_processor.update_submission")
        mock_update_submission.return_value = SubmissionDAO(
            id=1,
            filing=1,
            state=SubmissionState.SUBMISSION_UPLOAD_MALFORMED,
            filename="submission.csv",
        )

        mock_read_csv = mocker.patch("pandas.read_csv")
        mock_read_csv.side_effect = RuntimeError("File not in csv format")

        await submission_processor.validate_and_update_submission(
            "2024", "123456790", mock_sub, None, {"continue": True}
        )

        mock_update_submission.assert_called()
        log_mock.error.assert_called_with("The file is malformed", ANY, exc_info=True, stack_info=True)

        assert mock_update_submission.mock_calls[0].args[1].state == SubmissionState.VALIDATION_IN_PROGRESS
        assert mock_update_submission.mock_calls[1].args[1].state == SubmissionState.SUBMISSION_UPLOAD_MALFORMED

        mock_read_csv.side_effect = None
        mock_validation = mocker.patch("sbl_filing_api.services.submission_processor.validate_phases")
        mock_validation.side_effect = RuntimeError("File can not be parsed by validator")

        await submission_processor.validate_and_update_submission(
            "2024", "123456790", mock_sub, None, {"continue": True}
        )
        log_mock.error.assert_called_with("The file is malformed", ANY, exc_info=True, stack_info=True)
        assert mock_update_submission.mock_calls[0].args[1].state == SubmissionState.VALIDATION_IN_PROGRESS
        assert mock_update_submission.mock_calls[1].args[1].state == SubmissionState.SUBMISSION_UPLOAD_MALFORMED

    async def test_validation_expired(
        self,
        mocker: MockerFixture,
        validate_submission_mock: Mock,
        error_submission_mock: Mock,
        build_validation_results_mock: Mock,
        df_to_download_mock: Mock,
    ):
        log_mock = mocker.patch("sbl_filing_api.services.submission_processor.log")

        mock_sub = SubmissionDAO(
            id=1,
            filing=1,
            state=SubmissionState.SUBMISSION_UPLOADED,
            filename="submission.csv",
        )

        mock_update_submission = mocker.patch("sbl_filing_api.services.submission_processor.update_submission")
        mock_update_submission.return_value = SubmissionDAO(
            id=1,
            filing=1,
            state=SubmissionState.VALIDATION_IN_PROGRESS,
            filename="submission.csv",
        )

        await submission_processor.validate_and_update_submission(
            "2024", "123456790", mock_sub, None, {"continue": False}
        )

        # second update shouldn't be called
        assert len(mock_update_submission.mock_calls) == 1
        log_mock.warning.assert_called_with("Submission 1 is expired, will not be updating final state with results.")

    async def test_build_validation_results_success(self):
        result = (True, pd.DataFrame, ValidationPhase.LOGICAL.value)
        validation_results = submission_processor.build_validation_results(result)
        assert validation_results["syntax_errors"]["count"] == 0
        assert validation_results["logic_errors"]["count"] == 0
        assert validation_results["logic_warnings"]["count"] == 0

    async def test_build_validation_results_syntax_errors(self):
        result = (
            False,
            pd.DataFrame(
                [
                    [
                        1,
                        ValidationPhase.SYNTACTICAL.value,
                        "TESTLEI1234567890123",
                        "field_in_error",
                        1,
                        Severity.ERROR.value,
                        "test_link",
                        "VALID123",
                        "validation_name_goes_here",
                        "this is a val desc",
                        "multi-field",
                    ],
                ],
                columns=[
                    "record_no",
                    "validation_phase",
                    "uid",
                    "field_name",
                    "field_value",
                    "validation_severity",
                    "fig_link",
                    "validation_id",
                    "validation_name",
                    "validation_desc",
                    "scope",
                ],
            ),
            ValidationPhase.SYNTACTICAL.value,
        )
        validation_results = submission_processor.build_validation_results(result)
        assert validation_results["syntax_errors"]["count"] > 0

    async def test_build_validation_results_logic_warnings(self):
        result = (
            False,
            pd.DataFrame(
                [
                    [
                        1,
                        ValidationPhase.LOGICAL.value,
                        "TESTLEI1234567890123",
                        "field_in_error",
                        1,
                        Severity.WARNING.value,
                        "test_link",
                        "VALID123",
                        "validation_name_goes_here",
                        "this is a val desc",
                        "multi-field",
                    ],
                ],
                columns=[
                    "record_no",
                    "validation_phase",
                    "uid",
                    "field_name",
                    "field_value",
                    "validation_severity",
                    "fig_link",
                    "validation_id",
                    "validation_name",
                    "validation_desc",
                    "scope",
                ],
            ),
            ValidationPhase.LOGICAL.value,
        )
        validation_results = submission_processor.build_validation_results(result)
        assert validation_results["syntax_errors"]["count"] == 0
        assert validation_results["logic_errors"]["count"] == 0
        assert validation_results["logic_warnings"]["count"] > 0

    async def test_build_validation_results_logic_errors(self):
        result = (
            False,
            pd.DataFrame(
                [
                    [
                        1,
                        ValidationPhase.LOGICAL.value,
                        "TESTLEI1234567890123",
                        "field_in_error",
                        1,
                        Severity.ERROR.value,
                        "test_link",
                        "VALID123",
                        "validation_name_goes_here",
                        "this is a val desc",
                        "multi-field",
                    ],
                ],
                columns=[
                    "record_no",
                    "validation_phase",
                    "uid",
                    "field_name",
                    "field_value",
                    "validation_severity",
                    "fig_link",
                    "validation_id",
                    "validation_name",
                    "validation_desc",
                    "scope",
                ],
            ),
            ValidationPhase.LOGICAL.value,
        )
        validation_results = submission_processor.build_validation_results(result)
        assert validation_results["syntax_errors"]["count"] == 0
        assert validation_results["logic_errors"]["count"] > 0
        assert validation_results["logic_warnings"]["count"] == 0

    async def test_build_validation_results_logic_warnings_and_errors(self):
        result = (
            False,
            pd.DataFrame(
                [
                    [
                        1,
                        ValidationPhase.LOGICAL.value,
                        "TESTLEI1234567890123",
                        "field_in_error",
                        1,
                        Severity.WARNING.value,
                        "test_link",
                        "VALID123",
                        "validation_name_goes_here",
                        "this is a val desc",
                        "multi-field",
                    ],
                    [
                        2,
                        ValidationPhase.LOGICAL.value,
                        "TESTLEI1234567890123",
                        "field_in_error",
                        1,
                        Severity.ERROR.value,
                        "test_link",
                        "VALID234",
                        "validation_name_goes_here",
                        "this is a val desc",
                        "multi-field",
                    ],
                ],
                columns=[
                    "record_no",
                    "validation_phase",
                    "uid",
                    "field_name",
                    "field_value",
                    "validation_severity",
                    "fig_link",
                    "validation_id",
                    "validation_name",
                    "validation_desc",
                    "scope",
                ],
            ),
            ValidationPhase.LOGICAL.value,
        )
        validation_results = submission_processor.build_validation_results(result)
        assert validation_results["syntax_errors"]["count"] == 0
        assert validation_results["logic_errors"]["count"] > 0
        assert validation_results["logic_warnings"]["count"] > 0
