import pandas as pd
import pytest

from pytest_mock import MockerFixture
from textwrap import dedent
from unittest.mock import Mock
from regtech_data_validator.create_schemas import ValidationPhase
from regtech_data_validator.checks import Severity

from sbl_filing_api.entities.models.dao import SubmissionDAO, SubmissionState


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

    mock_read_csv = mocker.patch("pandas.read_csv")
    mock_read_csv.return_value = pd.DataFrame([["0", "1"]], columns=["Submission_Column_1", "Submission_Column_2"])

    return mock_update_submission


@pytest.fixture(scope="function")
def error_submission_mock(mocker: MockerFixture, validate_submission_mock: Mock):
    mock_validation = mocker.patch("sbl_filing_api.services.submission_processor.validate_phases")
    mock_validation.return_value = (False, pd.DataFrame([["Error"]], columns=["validation_severity"]))
    return validate_submission_mock


@pytest.fixture(scope="function")
def successful_submission_mock(mocker: MockerFixture, validate_submission_mock: Mock):
    mock_validation = mocker.patch("sbl_filing_api.services.submission_processor.validate_phases")
    mock_validation.return_value = (True, pd.DataFrame(columns=[], index=[]))
    return validate_submission_mock


@pytest.fixture(scope="function")
def warning_submission_mock(mocker: MockerFixture, validate_submission_mock: Mock):
    mock_validation = mocker.patch("sbl_filing_api.services.submission_processor.validate_phases")
    mock_validation.return_value = (False, pd.DataFrame([["Warning"]], columns=["validation_severity"]))
    return validate_submission_mock


@pytest.fixture(scope="function")
def validate_phases_success_mock(mocker: MockerFixture, validate_submission_mock: Mock):
    mock_json_formatting = mocker.patch("sbl_filing_api.services.submission_processor.validate_phases")
    mock_json_formatting.return_value = (True, pd.DataFrame(), ValidationPhase.LOGICAL.value)
    return mock_json_formatting


@pytest.fixture(scope="function")
def validate_phases_syntax_errors_mock(mocker: MockerFixture, validate_submission_mock: Mock):
    mock_json_formatting = mocker.patch("sbl_filing_api.services.submission_processor.validate_phases")
    mock_json_formatting.return_value = (
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
                    "single-field",
                ]
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
    return mock_json_formatting


@pytest.fixture(scope="function")
def validate_phases_logic_warnings_mock(mocker: MockerFixture, validate_submission_mock: Mock):
    mock_json_formatting = mocker.patch("sbl_filing_api.services.submission_processor.validate_phases")
    mock_json_formatting.return_value = (
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
                ]
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
    return mock_json_formatting


@pytest.fixture(scope="function")
def validate_phases_logic_errors_mock(mocker: MockerFixture, validate_submission_mock: Mock):
    mock_json_formatting = mocker.patch("sbl_filing_api.services.submission_processor.validate_phases")
    mock_json_formatting.return_value = (
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
                ]
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
    return mock_json_formatting


@pytest.fixture(scope="function")
def validate_phases_logic_warnings_and_errors_mock(mocker: MockerFixture, validate_submission_mock: Mock):
    mock_json_formatting = mocker.patch("sbl_filing_api.services.submission_processor.validate_phases")
    mock_json_formatting.return_value = (
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
    return mock_json_formatting


@pytest.fixture(scope="function")
def df_to_download_mock(mocker: MockerFixture):
    expected_output = dedent(
        """
                validation_type,validation_id,validation_name,row,unique_identifier,fig_link,validation_description,field_1,value_1
                Warning,W0003,uid.invalid_uid_lei,1,ZZZZZZZZZZZZZZZZZZZZZ1,https://www.consumerfinance.gov/data-research/small-business-lending/filing-instructions-guide/2024-guide/#4.4.1,"* The first 20 characters of the 'unique identifier' should
                match the Legal Entity Identifier (LEI) for the financial institution.
                ",uid,ZZZZZZZZZZZZZZZZZZZZZ1
                Warning,W0003,uid.invalid_uid_lei,2,ZZZZZZZZZZZZZZZZZZZZZS,https://www.consumerfinance.gov/data-research/small-business-lending/filing-instructions-guide/2024-guide/#4.4.1,"* The first 20 characters of the 'unique identifier' should
                match the Legal Entity Identifier (LEI) for the financial institution.
                ",uid,ZZZZZZZZZZZZZZZZZZZZZS
        """
    ).strip("\n")
    mock_download_formatting = mocker.patch("sbl_filing_api.services.submission_processor.df_to_download")
    mock_download_formatting.return_value = expected_output
    return mock_download_formatting
