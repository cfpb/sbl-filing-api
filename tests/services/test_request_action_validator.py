from http import HTTPStatus
from logging import Logger

import pytest

from fastapi import Request
from pytest_mock import MockerFixture
from regtech_api_commons.api.exceptions import RegTechHttpException

from sbl_filing_api.entities.models.dao import ContactInfoDAO, FilingDAO, SubmissionDAO
from sbl_filing_api.entities.models.model_enums import SubmissionState
from sbl_filing_api.services.request_action_validator import UserActionContext, set_context, validate_user_action


@pytest.fixture
def httpx_unauthed_mock(mocker: MockerFixture) -> None:
    mock_client_get = mocker.patch("httpx.AsyncClient.get")
    mock_response = mocker.patch("httpx.Response")
    mock_response.status_code = HTTPStatus.FORBIDDEN
    mock_client_get.return_value = mock_response


@pytest.fixture
def httpx_authed_mock(mocker: MockerFixture) -> None:
    mock_client_get = mocker.patch("httpx.AsyncClient.get")
    mock_response = mocker.patch("httpx.Response")
    mock_response.status_code = HTTPStatus.OK
    mock_response.json.return_value = {
        "tax_id": "12-3456789",
        "lei_status_code": "LAPSED",
        "lei_status": {"name": "Lapsed", "code": "LAPSED", "can_file": False},
    }
    mock_client_get.return_value = mock_response


@pytest.fixture
async def filing_mock(mocker: MockerFixture) -> FilingDAO:
    sub_mock = mocker.patch("sbl_filing_api.entities.models.dao.SubmissionDAO")
    sub_mock.state = SubmissionState.UPLOAD_FAILED
    filing = FilingDAO(lei="1234567890ABCDEFGH00", filing_period="2024", submissions=[sub_mock])
    return filing


@pytest.fixture
def request_mock(mocker: MockerFixture) -> Request:
    mock = mocker.patch("fastapi.Request")
    mock.path_params = {"lei": "1234567890ABCDEFGH00", "period_code": "2024"}
    return mock


@pytest.fixture
def request_mock_valid_context(mocker: MockerFixture, request_mock: Request, filing_mock: FilingDAO) -> Request:
    filing_mock.is_voluntary = True
    filing_mock.submissions = [SubmissionDAO(state=SubmissionState.SUBMISSION_ACCEPTED)]
    filing_mock.contact_info = ContactInfoDAO()

    request_mock.state.context = {
        "lei": "1234567890ABCDEFGH00",
        "period_code": "2024",
        UserActionContext.INSTITUTION: {
            "tax_id": "12-3456789",
            "lei_status_code": "ISSUED",
            "lei_status": {"name": "Issued", "code": "ISSUED", "can_file": True},
        },
        UserActionContext.FILING: filing_mock,
    }
    return request_mock


@pytest.fixture
def request_mock_invalid_context(mocker: MockerFixture, request_mock: Request, filing_mock: FilingDAO) -> Request:
    request_mock.state.context = {
        "lei": "1234567890ABCDEFGH00",
        "period_code": "2024",
        UserActionContext.INSTITUTION: {
            "lei_status_code": "LAPSED",
            "lei_status": {"name": "Lapsed", "code": "LAPSED", "can_file": False},
        },
        UserActionContext.FILING: filing_mock,
    }
    return request_mock


@pytest.fixture
def log_mock(mocker: MockerFixture) -> Logger:
    return mocker.patch("sbl_filing_api.services.request_action_validator.log")


async def test_validations_with_errors(request_mock_invalid_context: Request):
    run_validations = validate_user_action(
        {
            "valid_lei_status",
            "valid_lei_tin",
            "valid_filing_not_exists",
            "valid_sub_accepted",
            "valid_voluntary_filer",
            "valid_contact_info",
        },
        "Test Exception",
    )
    with pytest.raises(RegTechHttpException) as e:
        await run_validations(request_mock_invalid_context)
    assert e.value.name == "Test Exception"
    errors = e.value.detail
    assert (
        "Cannot sign filing. Filing for 1234567890ABCDEFGH00 for period 2024 does not have a latest submission in the SUBMISSION_ACCEPTED state."
        in errors
    )
    assert (
        "Cannot sign filing. Filing for 1234567890ABCDEFGH00 for period 2024 does not have a selection of is_voluntary defined."
        in errors
    )
    assert (
        "Cannot sign filing. Filing for 1234567890ABCDEFGH00 for period 2024 does not have contact info defined."
        in errors
    )
    assert "Cannot sign filing. TIN is required to file." in errors
    assert "Cannot sign filing. LEI status of LAPSED cannot file." in errors


async def test_validations_no_errors(request_mock_valid_context: Request):
    run_validations = validate_user_action(
        {
            "valid_lei_status",
            "valid_lei_tin",
            "valid_filing_exists",
            "valid_sub_accepted",
            "valid_voluntary_filer",
            "valid_contact_info",
        },
        "Test Exception",
    )
    await run_validations(request_mock_valid_context)


async def test_lei_status_bad_api_res(request_mock: Request, httpx_unauthed_mock):
    run_validations = validate_user_action({"valid_lei_status"}, "Test Exception")
    context_setter = set_context({UserActionContext.INSTITUTION})
    await context_setter(request_mock)

    with pytest.raises(RegTechHttpException) as e:
        await run_validations(request_mock)
    assert "Unable to determine LEI status." in e.value.detail


async def test_lei_status_good_api_res(request_mock: Request, httpx_authed_mock):
    run_validations = validate_user_action({"valid_lei_status"}, "Test Exception")
    context_setter = set_context({UserActionContext.INSTITUTION})
    await context_setter(request_mock)
    with pytest.raises(RegTechHttpException) as e:
        await run_validations(request_mock)
    assert "Cannot sign filing. LEI status of LAPSED cannot file." in e.value.detail


async def test_invalid_validation(request_mock_invalid_context: Request, log_mock: Logger):
    run_validations = validate_user_action({"fake_validation"}, "Test Exception")
    await run_validations(request_mock_invalid_context)
    log_mock.warning.assert_called_with("Action validator [%s] not found.", "fake_validation")
