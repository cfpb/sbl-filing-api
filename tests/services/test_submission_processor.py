import polars as pl
import pytest

from http import HTTPStatus
from sbl_filing_api.services import submission_processor
from fastapi import HTTPException
from unittest.mock import Mock
from pytest_mock import MockerFixture
from sbl_filing_api.config import settings
from sbl_filing_api.entities.models.dao import SubmissionDAO, SubmissionState
from regtech_data_validator.validation_results import ValidationPhase, ValidationResults, Counts
from regtech_data_validator.checks import Severity
from regtech_api_commons.api.exceptions import RegTechHttpException


class TestSubmissionProcessor:
    @pytest.fixture
    def mock_upload_file(self, mocker: MockerFixture) -> Mock:
        file_mock = mocker.patch("fastapi.UploadFile")
        return file_mock.return_value

    async def test_upload(self, mocker: MockerFixture):
        upload_mock = mocker.patch("sbl_filing_api.services.file_handler.upload")
        submission_processor.upload_to_storage("test_period", "test", "test", b"test content local")
        upload_mock.assert_called_once_with(path="upload/test_period/test/test.csv", content=b"test content local")

    async def test_read_from_storage(self, mocker: MockerFixture):
        download_mock = mocker.patch("sbl_filing_api.services.file_handler.download")
        submission_processor.get_from_storage("2024", "1234567890", "1_report")
        download_mock.assert_called_with("upload/2024/1234567890/1_report.csv")

    async def test_upload_failure(self, mocker: MockerFixture):
        upload_mock = mocker.patch("sbl_filing_api.services.file_handler.upload")
        upload_mock.side_effect = IOError("test")
        with pytest.raises(Exception) as e:
            submission_processor.upload_to_storage("test_period", "test", "test", b"test content")
        assert isinstance(e.value, RegTechHttpException)
        assert e.value.name == "Upload Failure"

    async def test_read_failure(self, mocker: MockerFixture):
        download_mock = mocker.patch("sbl_filing_api.services.file_handler.download")
        download_mock.side_effect = IOError("test")
        with pytest.raises(Exception) as e:
            submission_processor.get_from_storage("2024", "1234567890", "1_report")
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
    ):
        mock_sub = SubmissionDAO(
            id=1,
            filing=1,
            counter=2,
            state=SubmissionState.SUBMISSION_UPLOADED,
            filename="submission.csv",
        )
        successful_submission_mock.return_value.counter = 2

        mock_download_formatting = mocker.patch("sbl_filing_api.services.submission_processor.df_to_download")
        mock_download_formatting.return_value = b"\x01"

        file_mock = mocker.patch("sbl_filing_api.services.submission_processor.upload_to_storage")

        await submission_processor.validate_and_update_submission(
            "2024", "123456790", mock_sub, None, {"continue": True}
        )

        file_mock.assert_called_once_with(
            "2024",
            "123456790",
            "2" + submission_processor.REPORT_QUALIFIER,
            mock_download_formatting.return_value,
        )
        assert successful_submission_mock.mock_calls[0].args[1].state == SubmissionState.VALIDATION_IN_PROGRESS
        assert successful_submission_mock.mock_calls[0].args[1].validation_ruleset_version == "0.1.0"
        assert successful_submission_mock.mock_calls[1].args[1].state == "VALIDATION_SUCCESSFUL"

    async def test_validate_and_update_warnings(
        self,
        mocker: MockerFixture,
        warning_submission_mock: Mock,
    ):
        mock_sub = SubmissionDAO(
            id=1,
            filing=1,
            counter=3,
            state=SubmissionState.SUBMISSION_UPLOADED,
            filename="submission.csv",
        )
        warning_submission_mock.return_value.counter = 3

        mock_build_json = mocker.patch("sbl_filing_api.services.submission_processor.build_validation_results")
        mock_build_json.return_value = {"logic_errors": {"total_count": 0}, "logic_warnings": {"total_count": 1}}

        mock_download_formatting = mocker.patch("sbl_filing_api.services.submission_processor.df_to_download")
        mock_download_formatting.return_value = b"\x01"

        file_mock = mocker.patch("sbl_filing_api.services.submission_processor.upload_to_storage")

        await submission_processor.validate_and_update_submission(
            "2024", "123456790", mock_sub, None, {"continue": True}
        )

        file_mock.assert_called_once_with(
            "2024",
            "123456790",
            "3" + submission_processor.REPORT_QUALIFIER,
            mock_download_formatting.return_value,
        )
        assert warning_submission_mock.mock_calls[0].args[1].state == SubmissionState.VALIDATION_IN_PROGRESS
        assert warning_submission_mock.mock_calls[0].args[1].validation_ruleset_version == "0.1.0"
        assert warning_submission_mock.mock_calls[1].args[1].state == SubmissionState.VALIDATION_WITH_WARNINGS

    async def test_validate_and_update_errors(
        self,
        mocker: MockerFixture,
        error_submission_mock: Mock,
    ):
        mock_sub = SubmissionDAO(
            id=1,
            filing=1,
            counter=4,
            state=SubmissionState.SUBMISSION_UPLOADED,
            filename="submission.csv",
        )
        error_submission_mock.return_value.counter = 4

        mock_build_json = mocker.patch("sbl_filing_api.services.submission_processor.build_validation_results")
        mock_build_json.return_value = {"logic_errors": {"total_count": 1}}

        mock_download_formatting = mocker.patch("sbl_filing_api.services.submission_processor.df_to_download")
        mock_download_formatting.return_value = b"\x01"

        file_mock = mocker.patch("sbl_filing_api.services.submission_processor.upload_to_storage")

        await submission_processor.validate_and_update_submission(
            "2024", "123456790", mock_sub, None, {"continue": True}
        )

        file_mock.assert_called_once_with(
            "2024",
            "123456790",
            "4" + submission_processor.REPORT_QUALIFIER,
            mock_download_formatting.return_value,
        )
        assert error_submission_mock.mock_calls[0].args[1].state == SubmissionState.VALIDATION_IN_PROGRESS
        assert error_submission_mock.mock_calls[0].args[1].validation_ruleset_version == "0.1.0"
        assert error_submission_mock.mock_calls[1].args[1].state == SubmissionState.VALIDATION_WITH_ERRORS

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

        mock_read_csv = mocker.patch("sbl_filing_api.services.submission_processor.validate_batch_csv")
        re = RuntimeError("File not in csv format")
        mock_read_csv.side_effect = re

        await submission_processor.validate_and_update_submission(
            "2024", "123456790", mock_sub, None, {"continue": True}
        )

        mock_update_submission.assert_called()
        log_mock.exception.assert_called_with("The file is malformed.")

        assert mock_update_submission.mock_calls[0].args[1].state == SubmissionState.VALIDATION_IN_PROGRESS
        assert mock_update_submission.mock_calls[1].args[1].state == SubmissionState.SUBMISSION_UPLOAD_MALFORMED

        mock_read_csv.side_effect = None
        mock_validation = mocker.patch("sbl_filing_api.services.submission_processor.validate_batch_csv")
        re = RuntimeError("File can not be parsed by validator")
        mock_validation.side_effect = re

        await submission_processor.validate_and_update_submission(
            "2024", "123456790", mock_sub, None, {"continue": True}
        )
        log_mock.exception.assert_called_with("The file is malformed.")
        assert mock_update_submission.mock_calls[0].args[1].state == SubmissionState.VALIDATION_IN_PROGRESS
        assert mock_update_submission.mock_calls[1].args[1].state == SubmissionState.SUBMISSION_UPLOAD_MALFORMED

        e = Exception("Test exception")
        mock_validation.side_effect = e

        await submission_processor.validate_and_update_submission(
            "2024", "123456790", mock_sub, None, {"continue": True}
        )
        log_mock.exception.assert_called_with(
            "Validation for submission %d did not complete due to an unexpected error.", mock_sub.id
        )

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

        mock_build_json = mocker.patch("sbl_filing_api.services.submission_processor.build_validation_results")
        mock_build_json.return_value = {"logic_errors": {"total_count": 1}}

        await submission_processor.validate_and_update_submission(
            "2024", "123456790", mock_sub, None, {"continue": False}
        )

        # second update shouldn't be called
        assert len(mock_update_submission.mock_calls) == 1
        log_mock.warning.assert_called_with("Submission 1 is expired, will not be updating final state with results.")

    async def test_build_validation_results_success(self, mocker: MockerFixture):

        df_to_dicts_mock = mocker.patch("sbl_filing_api.services.submission_processor.df_to_dicts")
        df_to_dicts_mock.return_value = []

        validation_results = submission_processor.build_validation_results(pl.DataFrame(), [], ValidationPhase.LOGICAL)
        assert validation_results["syntax_errors"]["single_field_count"] == 0
        assert validation_results["syntax_errors"]["multi_field_count"] == 0
        assert validation_results["syntax_errors"]["register_count"] == 0
        assert validation_results["logic_errors"]["single_field_count"] == 0
        assert validation_results["logic_errors"]["multi_field_count"] == 0
        assert validation_results["logic_errors"]["register_count"] == 0
        assert validation_results["logic_warnings"]["single_field_count"] == 0
        assert validation_results["logic_warnings"]["multi_field_count"] == 0
        assert validation_results["logic_warnings"]["register_count"] == 0

    async def test_build_validation_results_syntax_errors(self, mocker: MockerFixture):

        df_to_dicts_mock = mocker.patch("sbl_filing_api.services.submission_processor.df_to_dicts")
        df_to_dicts_mock.return_value = [
            {
                "validation": {
                    "id": "E0001",
                    "name": "uid.invalid_text_length",
                    "description": "* 'Unique identifier' must be at least 21 characters in\nlength and at most 45 characters in length.",
                    "severity": "Error",
                    "scope": "single-field",
                    "fig_link": "https://www.consumerfinance.gov/data-research/small-business-lending/filing-instructions-guide/2024-guide/#4.1.1",
                },
                "records": [
                    {
                        "record_no": 1,
                        "uid": "12345",
                        "fields": [{"name": "uid", "value": "12345"}],
                    }
                ],
            },
            {
                "validation": {
                    "id": "E0002",
                    "name": "uid.invalid_text_pattern",
                    "description": "* 'Unique identifier' may contain any combination of numbers and/or uppercase letters (i.e., 0-9 and A-Z), and must **not** contain any other characters.",
                    "severity": "Error",
                    "scope": "single-field",
                    "fig_link": "https://www.consumerfinance.gov/data-research/small-business-lending/filing-instructions-guide/2024-guide/#4.1.2",
                },
                "records": [
                    {
                        "record_no": 1,
                        "uid": "123-45",
                        "fields": [{"name": "uid", "value": "123-45"}],
                    }
                ],
            },
        ]
        findings = pl.DataFrame(
            {
                "validation_type": [Severity.ERROR, Severity.ERROR, Severity.WARNING],
                "scope": ["single-field", "single-field", "multi-field"],
            }
        )
        result_counts = ValidationResults(
            error_counts=Counts(single_field_count=2),
            warning_counts=Counts(),
            is_valid=False,
            findings=findings,
            phase=ValidationPhase.SYNTACTICAL,
        )

        validation_results = submission_processor.build_validation_results(
            findings, [result_counts], ValidationPhase.SYNTACTICAL
        )
        assert validation_results["syntax_errors"]["single_field_count"] == 2
        assert validation_results["syntax_errors"]["multi_field_count"] == 0
        assert validation_results["syntax_errors"]["register_count"] == 0

    def test_build_validation_results_logic_errors(self, mocker: MockerFixture):

        df_to_dicts_mock = mocker.patch("sbl_filing_api.services.submission_processor.df_to_dicts")
        df_to_dicts_mock.return_value = [
            {
                "validation": {
                    "id": "E3000",
                    "name": "uid.duplicates_in_dataset",
                    "description": "* Any 'unique identifier' may **not** be used in more than one \nrecord within a small business lending application register.\n",
                    "severity": "Error",
                    "scope": "register",
                    "fig_link": "https://www.consumerfinance.gov/data-research/small-business-lending/filing-instructions-guide/2024-guide/#4.3.1",
                },
                "records": [
                    {
                        "record_no": 1,
                        "uid": "12345678901234567890",
                        "fields": [{"name": "uid", "value": "12345678901234567890"}],
                    },
                    {
                        "record_no": 2,
                        "uid": "12345678901234567890",
                        "fields": [{"name": "uid", "value": "12345678901234567890"}],
                    },
                ],
            },
        ]
        findings = pl.DataFrame(
            {
                "validation_type": [Severity.ERROR, Severity.ERROR, Severity.WARNING],
                "scope": ["register", "register", "multi-field"],
            }
        )

        result_counts = ValidationResults(
            error_counts=Counts(register_count=2),
            warning_counts=Counts(),
            is_valid=False,
            findings=findings,
            phase=ValidationPhase.LOGICAL,
        )

        validation_results = submission_processor.build_validation_results(
            findings, [result_counts], ValidationPhase.LOGICAL
        )
        assert validation_results["logic_errors"]["single_field_count"] == 0
        assert validation_results["logic_errors"]["multi_field_count"] == 0
        assert validation_results["logic_errors"]["register_count"] == 2

    def test_build_validation_results_logic_warnings(self, mocker: MockerFixture):

        df_to_dicts_mock = mocker.patch("sbl_filing_api.services.submission_processor.df_to_dicts")
        df_to_dicts_mock.return_value = [
            {
                "validation": {
                    "id": "W0003",
                    "name": "uid.invalid_uid_lei",
                    "description": "* The first 20 characters of the 'unique identifier' should\nmatch the Legal Entity Identifier (LEI) for the financial institution.",
                    "severity": "Warning",
                    "scope": "single-field",
                    "fig_link": "https://www.consumerfinance.gov/data-research/small-business-lending/filing-instructions-guide/2024-guide/#4.4.1",
                },
                "records": [
                    {
                        "record_no": 3,
                        "uid": "12345678901234567891",
                        "fields": [{"name": "uid", "value": "12345678901234567891"}],
                    }
                ],
            },
        ]

        findings = pl.DataFrame({"validation_type": [Severity.WARNING], "scope": ["single-field"]})

        result_counts = ValidationResults(
            error_counts=Counts(),
            warning_counts=Counts(single_field_count=1),
            is_valid=False,
            findings=findings,
            phase=ValidationPhase.LOGICAL,
        )

        validation_results = submission_processor.build_validation_results(
            findings, [result_counts], ValidationPhase.LOGICAL
        )
        assert validation_results["logic_warnings"]["single_field_count"] == 1
        assert validation_results["logic_warnings"]["multi_field_count"] == 0
        assert validation_results["logic_warnings"]["register_count"] == 0

    def test_build_validation_results_logic_warnings_and_errors(self, mocker: MockerFixture):

        df_to_dicts_mock = mocker.patch("sbl_filing_api.services.submission_processor.df_to_dicts")
        df_to_dicts_mock.return_value = [
            {
                "validation": {
                    "id": "W0003",
                    "name": "uid.invalid_uid_lei",
                    "description": "* The first 20 characters of the 'unique identifier' should\nmatch the Legal Entity Identifier (LEI) for the financial institution.",
                    "severity": "Warning",
                    "scope": "single-field",
                    "fig_link": "https://www.consumerfinance.gov/data-research/small-business-lending/filing-instructions-guide/2024-guide/#4.4.1",
                },
                "records": [
                    {
                        "record_no": 3,
                        "uid": "12345678901234567891",
                        "fields": [{"name": "uid", "value": "12345678901234567891"}],
                    }
                ],
            },
            {
                "validation": {
                    "id": "E3000",
                    "name": "uid.duplicates_in_dataset",
                    "description": "* Any 'unique identifier' may **not** be used in more than one \nrecord within a small business lending application register.\n",
                    "severity": "Error",
                    "scope": "register",
                    "fig_link": "https://www.consumerfinance.gov/data-research/small-business-lending/filing-instructions-guide/2024-guide/#4.3.1",
                },
                "records": [
                    {
                        "record_no": 1,
                        "uid": "12345678901234567890",
                        "fields": [{"name": "uid", "value": "12345678901234567890"}],
                    },
                    {
                        "record_no": 2,
                        "uid": "12345678901234567890",
                        "fields": [{"name": "uid", "value": "12345678901234567890"}],
                    },
                ],
            },
        ]

        findings = pl.DataFrame(
            {
                "validation_type": [Severity.ERROR, Severity.ERROR, Severity.WARNING],
                "scope": ["register", "register", "single-field"],
            }
        )

        result_counts = ValidationResults(
            error_counts=Counts(register_count=2),
            warning_counts=Counts(single_field_count=1),
            is_valid=False,
            findings=findings,
            phase=ValidationPhase.LOGICAL,
        )

        validation_results = submission_processor.build_validation_results(
            findings, [result_counts], ValidationPhase.LOGICAL
        )
        assert validation_results["logic_warnings"]["single_field_count"] == 1
        assert validation_results["logic_warnings"]["multi_field_count"] == 0
        assert validation_results["logic_warnings"]["register_count"] == 0
        assert validation_results["logic_errors"]["single_field_count"] == 0
        assert validation_results["logic_errors"]["multi_field_count"] == 0
        assert validation_results["logic_errors"]["register_count"] == 2
