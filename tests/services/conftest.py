import pandas as pd
import pytest

from pytest_mock import MockerFixture
from unittest.mock import Mock

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
def df_to_json_mock(mocker: MockerFixture, validate_submission_mock: Mock):
    mock_json_formatting = mocker.patch("sbl_filing_api.services.submission_processor.df_to_json")
    mock_json_formatting.return_value = "[{}]"
    return mock_json_formatting
