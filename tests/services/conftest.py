import pandas as pd
import pytest

from pytest_mock import MockerFixture
from textwrap import dedent
from unittest.mock import Mock

from sbl_filing_api.entities.models.dao import SubmissionDAO, SubmissionState

from regtech_data_validator.validation_results import ValidationResults, ValidationPhase


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
    mock_validation.return_value = ValidationResults(
        phase=ValidationPhase.SYNTACTICAL,
        single_field_count=1,
        multi_field_count=0,
        register_count=0,
        findings=pd.DataFrame([["Error"]], columns=["validation_severity"]),
        is_valid=False,
    )
    return validate_submission_mock


@pytest.fixture(scope="function")
def successful_submission_mock(mocker: MockerFixture, validate_submission_mock: Mock):
    mock_validation = mocker.patch("sbl_filing_api.services.submission_processor.validate_phases")
    mock_validation.return_value = ValidationResults(
        phase=ValidationPhase.LOGICAL,
        single_field_count=0,
        multi_field_count=0,
        register_count=0,
        findings=pd.DataFrame(),
        is_valid=True,
    )
    return validate_submission_mock


@pytest.fixture(scope="function")
def warning_submission_mock(mocker: MockerFixture, validate_submission_mock: Mock):
    mock_validation = mocker.patch("sbl_filing_api.services.submission_processor.validate_phases")
    mock_validation.return_value = ValidationResults(
        phase=ValidationPhase.LOGICAL,
        single_field_count=1,
        multi_field_count=0,
        register_count=0,
        findings=pd.DataFrame([["Warning"]], columns=["validation_severity"]),
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
