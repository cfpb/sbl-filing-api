import polars as pl
import pytest

from pytest_mock import MockerFixture
from unittest.mock import Mock

from sbl_filing_api.entities.models.dao import SubmissionDAO, SubmissionState

from regtech_data_validator.validation_results import ValidationResults, ValidationPhase, Counts
from regtech_data_validator.checks import Severity


@pytest.fixture(scope="function")
def validate_submission_mock(mocker: MockerFixture):
    return_sub = SubmissionDAO(
        id=1,
        filing=1,
        state=SubmissionState.VALIDATION_IN_PROGRESS,
        filename="submission.csv",
    )
    mock_update_submission = mocker.patch("sbl_filing_api.services.submission_processor.update_submission")
    mock_update_submission.return_value = return_sub

    return mock_update_submission


@pytest.fixture(scope="function")
def error_submission_mock(mocker: MockerFixture, validate_submission_mock: Mock):

    mock_read_csv = mocker.patch("sbl_filing_api.services.submission_processor.validate_batch_csv")
    mock_read_csv.return_value = iter([(pl.DataFrame({"validation_type": [Severity.ERROR]}), ValidationPhase.LOGICAL)])

    mock_validation = mocker.patch("sbl_filing_api.services.submission_processor.build_validation_results")
    mock_validation.return_value = ValidationResults(
        phase=ValidationPhase.SYNTACTICAL,
        error_counts=Counts(
            single_field_count=1,
            multi_field_count=0,
            register_count=0,
            total_count=1,
        ),
        warning_counts=Counts(single_field_count=0, multi_field_count=0, register_count=0, total_count=0),
        findings=pl.DataFrame({"validation_severity": [Severity.ERROR]}),
        is_valid=False,
    )
    return validate_submission_mock


@pytest.fixture(scope="function")
def successful_submission_mock(mocker: MockerFixture, validate_submission_mock: Mock):

    mock_read_csv = mocker.patch("sbl_filing_api.services.submission_processor.validate_batch_csv")
    mock_read_csv.return_value = iter(())

    mock_validation = mocker.patch("sbl_filing_api.services.submission_processor.build_validation_results")
    mock_validation.return_value = ValidationResults(
        phase=ValidationPhase.LOGICAL,
        error_counts=Counts(
            single_field_count=0,
            multi_field_count=0,
            register_count=0,
            total_count=0,
        ),
        warning_counts=Counts(single_field_count=0, multi_field_count=0, register_count=0, total_count=0),
        findings=pl.DataFrame(),
        is_valid=True,
    )
    return validate_submission_mock


@pytest.fixture(scope="function")
def warning_submission_mock(mocker: MockerFixture, validate_submission_mock: Mock):

    mock_read_csv = mocker.patch("sbl_filing_api.services.submission_processor.validate_batch_csv")
    mock_read_csv.return_value = iter(
        [(pl.DataFrame({"validation_type": [Severity.WARNING]}), ValidationPhase.LOGICAL)]
    )

    mock_validation = mocker.patch("sbl_filing_api.services.submission_processor.build_validation_results")
    mock_validation.return_value = ValidationResults(
        phase=ValidationPhase.LOGICAL,
        error_counts=Counts(
            single_field_count=0,
            multi_field_count=0,
            register_count=0,
            total_count=0,
        ),
        warning_counts=Counts(single_field_count=1, multi_field_count=0, register_count=0, total_count=1),
        findings=pl.DataFrame({"validation_severity": Severity.WARNING}),
        is_valid=False,
    )
    return validate_submission_mock


@pytest.fixture(scope="function")
def build_validation_results_mock(mocker: MockerFixture, validate_submission_mock: Mock):
    mock_json_formatting = mocker.patch("sbl_filing_api.services.submission_processor.build_validation_results")
    mock_json_formatting.return_value = "{}"
    return mock_json_formatting


@pytest.fixture(scope="function")
def df_to_download_mock(mocker: MockerFixture):
    mock_download_formatting = mocker.patch("sbl_filing_api.services.submission_processor.df_to_download")
    mock_download_formatting.return_value = None
