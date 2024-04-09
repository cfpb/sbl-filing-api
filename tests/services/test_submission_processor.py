from http import HTTPStatus
from sbl_filing_api.services import submission_processor
from fastapi import HTTPException
import pytest
from unittest.mock import Mock, ANY
from pytest_mock import MockerFixture
from sbl_filing_api.config import FsProtocol, settings
from sbl_filing_api.entities.models.dao import SubmissionDAO, SubmissionState


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
        with mocker.mock_open(mock_fs.open):
            await submission_processor.get_from_storage("2024", "1234567890", "1_report")
        mock_fs_func.assert_called()
        mock_fs.open.assert_called_with("../upload/upload/2024/1234567890/1_report.csv", "r")
        file_handle = mock_fs.open()
        file_handle.read.assert_called_with()

    async def test_upload_s3_no_mkdir(self, mocker: MockerFixture, mock_fs_func: Mock, mock_fs: Mock):
        default_fs_proto = settings.upload_fs_protocol
        settings.upload_fs_protocol = FsProtocol.S3
        with mocker.mock_open(mock_fs.open):
            await submission_processor.upload_to_storage("test_period", "test", "test", b"test content s3")
        mock_fs_func.assert_called()
        mock_fs.mkdirs.assert_not_called()
        mock_fs.open.assert_called_with("../upload/upload/test_period/test/test.csv", "wb")
        file_handle = mock_fs.open()
        file_handle.write.assert_called_with(b"test content s3")
        settings.upload_fs_protocol = default_fs_proto

    async def test_upload_failure(self, mocker: MockerFixture, mock_fs_func: Mock, mock_fs: Mock):
        log_mock = mocker.patch("sbl_filing_api.services.submission_processor.log")
        mock_fs.mkdirs.side_effect = IOError("test")
        with pytest.raises(Exception) as e:
            await submission_processor.upload_to_storage("test_period", "test", "test", b"test content")
        log_mock.error.assert_called_with("Failed to upload file", ANY, exc_info=True, stack_info=True)
        assert isinstance(e.value, HTTPException)

    async def test_read_failure(self, mocker: MockerFixture, mock_fs_func: Mock, mock_fs: Mock):
        log_mock = mocker.patch("sbl_filing_api.services.submission_processor.log")
        mock_fs.open.side_effect = IOError("test")
        with pytest.raises(Exception) as e:
            await submission_processor.get_from_storage("2024", "1234567890", "1_report")
        log_mock.error.assert_called_with(
            "Failed to read file ../upload/upload/2024/1234567890/1_report.csv:", ANY, exc_info=True, stack_info=True
        )
        assert isinstance(e.value, HTTPException)

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
        self, mocker: MockerFixture, successful_submission_mock: Mock, df_to_json_mock: Mock, df_to_download_mock: Mock
    ):
        mock_sub = SubmissionDAO(
            id=1,
            filing=1,
            state=SubmissionState.SUBMISSION_UPLOADED,
            filename="submission.csv",
        )
        file_mock = mocker.patch("sbl_filing_api.services.submission_processor.upload_to_storage")
        df_to_download_mock.return_value = ""

        await submission_processor.validate_and_update_submission("2024", "123456790", mock_sub, None)
        encoded_results = df_to_download_mock.return_value.encode("utf-8")
        assert file_mock.mock_calls[0].args == (
            "2024",
            "123456790",
            "1" + submission_processor.REPORT_QUALIFIER,
            encoded_results,
        )
        assert successful_submission_mock.mock_calls[0].args[0].state == SubmissionState.VALIDATION_IN_PROGRESS
        assert successful_submission_mock.mock_calls[0].args[0].validation_ruleset_version == "0.1.0"
        assert successful_submission_mock.mock_calls[1].args[0].state == "VALIDATION_SUCCESSFUL"

    async def test_validate_and_update_warnings(
        self, mocker: MockerFixture, warning_submission_mock: Mock, df_to_json_mock: Mock, df_to_download_mock: Mock
    ):
        mock_sub = SubmissionDAO(
            id=1,
            filing=1,
            state=SubmissionState.SUBMISSION_UPLOADED,
            filename="submission.csv",
        )
        file_mock = mocker.patch("sbl_filing_api.services.submission_processor.upload_to_storage")

        await submission_processor.validate_and_update_submission("2024", "123456790", mock_sub, None)
        encoded_results = df_to_download_mock.return_value.encode("utf-8")
        assert file_mock.mock_calls[0].args == (
            "2024",
            "123456790",
            "1" + submission_processor.REPORT_QUALIFIER,
            encoded_results,
        )
        assert warning_submission_mock.mock_calls[0].args[0].state == SubmissionState.VALIDATION_IN_PROGRESS
        assert warning_submission_mock.mock_calls[0].args[0].validation_ruleset_version == "0.1.0"
        assert warning_submission_mock.mock_calls[1].args[0].state == "VALIDATION_WITH_WARNINGS"

    async def test_validate_and_update_errors(
        self, mocker: MockerFixture, error_submission_mock: Mock, df_to_json_mock: Mock, df_to_download_mock: Mock
    ):
        mock_sub = SubmissionDAO(
            id=1,
            filing=1,
            state=SubmissionState.SUBMISSION_UPLOADED,
            filename="submission.csv",
        )

        file_mock = mocker.patch("sbl_filing_api.services.submission_processor.upload_to_storage")

        await submission_processor.validate_and_update_submission("2024", "123456790", mock_sub, None)
        encoded_results = df_to_download_mock.return_value.encode("utf-8")
        assert file_mock.mock_calls[0].args == (
            "2024",
            "123456790",
            "1" + submission_processor.REPORT_QUALIFIER,
            encoded_results,
        )
        assert error_submission_mock.mock_calls[0].args[0].state == SubmissionState.VALIDATION_IN_PROGRESS
        assert error_submission_mock.mock_calls[0].args[0].validation_ruleset_version == "0.1.0"
        assert error_submission_mock.mock_calls[1].args[0].state == "VALIDATION_WITH_ERRORS"
