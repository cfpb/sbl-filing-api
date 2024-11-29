import inspect
import json
import logging
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, Dict, List, Set

import httpx
from async_lru import alru_cache
from fastapi import Request, status
from regtech_api_commons.api.exceptions import RegTechHttpException

from sbl_filing_api.config import settings
from sbl_filing_api.entities.models.dao import FilingDAO, SubmissionDAO
from sbl_filing_api.entities.models.model_enums import SubmissionState
from sbl_filing_api.entities.repos import submission_repo as repo

log = logging.getLogger(__name__)


class UserActionContext(StrEnum):
    FILING = "filing"
    INSTITUTION = "institution"


class FiRequest:
    """
    FI retrieval request to allow cache to work
    """

    request: Request
    lei: str

    def __init__(self, request: Request, lei: str):
        self.request = request
        self.lei = lei

    def __hash__(self):
        return hash(self.lei)

    def __eq__(self, other: "FiRequest"):
        return self.lei == other.lei


@alru_cache(ttl=60 * 60)
async def get_institution_data(fi_request: FiRequest):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            settings.user_fi_api_url + fi_request.lei,
            headers={"authorization": fi_request.request.headers["authorization"]},
        )
        return res.json()


class ActionValidator(ABC):
    """
    Abstract Callable class for action validations, __subclasses__ method leveraged to construct a registry
    """

    name: str

    def __init__(self, name: str):
        super().__init__()
        self.name = name

    @abstractmethod
    def __call__(self, *args, **kwargs): ...


class CheckLeiStatus(ActionValidator):
    def __init__(self):
        super().__init__("check_lei_status")

    def __call__(self, institution: Dict[str, Any], **kwargs):
        try:
            is_active = institution["lei_status"]["can_file"]
            if not is_active:
                return f"LEI status of {institution['lei_status_code']} cannot file."
        except Exception:
            log.exception("Unable to determine lei status: %s", json.dumps(institution))
            return "Unable to determine LEI status."


class CheckLeiTin(ActionValidator):
    def __init__(self):
        super().__init__("check_lei_tin")

    def __call__(self, institution: Dict[str, Any], **kwargs):
        if not institution["tax_id"]:
            return "TIN is required to file"


class CheckFilingExists(ActionValidator):
    def __init__(self):
        super().__init__("check_filing_exists")

    def __call__(self, filing: FilingDAO, lei: str, period: str, **kwargs):
        if not filing:
            return f"There is no Filing for LEI {lei} in period {period}, unable to sign a non-existent Filing."


class CheckSubAccepted(ActionValidator):
    def __init__(self):
        super().__init__("check_sub_accepted")

    async def __call__(self, filing: FilingDAO, **kwargs):
        submissions: List[SubmissionDAO] = await filing.awaitable_attrs.submissions
        if not len(submissions) or submissions[0].state != SubmissionState.SUBMISSION_ACCEPTED:
            filing.lei
            filing.filing_period
            return f"Cannot sign filing. Filing for {filing.lei} for period {filing.filing_period} does not have a latest submission in the SUBMISSION_ACCEPTED state."


class CheckVoluntaryFiler(ActionValidator):
    def __init__(self):
        super().__init__("check_voluntary_filer")

    def __call__(self, filing: FilingDAO, **kwargs):
        if filing.is_voluntary is None:
            return f"Cannot sign filing. Filing for {filing.lei} for period {filing.filing_period} does not have a selection of is_voluntary defined."


class CheckContactInfo(ActionValidator):
    def __init__(self):
        super().__init__("check_contact_info")

    def __call__(self, filing: FilingDAO, **kwargs):
        if not filing.contact_info:
            return f"Cannot sign filing. Filing for {filing.lei} for period {filing.filing_period} does not have contact info defined."


validation_registry = {Validator() for Validator in ActionValidator.__subclasses__()}


def set_context(requirements: Set[UserActionContext]):
    """
    Sets a `context` object on `request.state`; this should typically include the institution, and filing;
    `context` should be set before running any validation dependencies
    Args:
        requst (Request): request from the API endpoint
        lei: comes from request path param
        period: filing period comes from request path param
    """

    async def _set_context(request: Request):
        lei = request.path_params.get("lei")
        period = request.path_params.get("period_code")
        context = {"lei": lei, "period": period}
        if lei and UserActionContext.INSTITUTION in requirements:

            context = context | {UserActionContext.INSTITUTION: await get_institution_data(FiRequest(request, lei))}
        if period and UserActionContext.FILING in requirements:
            context = context | {UserActionContext.FILING: await repo.get_filing(request.state.db_session, lei, period)}
        request.state.context = context

    return _set_context


def validate_user_action(validator_names: Set[str], exception_name: str):
    """
    Runs through list of validators, and aggregate into one exception to allow users know what all the errors are.

    Args:
        validator_names (List[str]): list of names of the validators matching the ActionValidator.name attribute,
          this is passed in from the endpoint dependency based on RequestActionValidations setting
          configurable via `request_validators__` prefixed env vars
    """

    async def _run_validations(request: Request):
        res = []
        validators = set(filter(lambda validator: validator.name in validator_names, validation_registry))
        for validator in validators:
            if inspect.iscoroutinefunction(validator.__call__):
                res.append(await validator(**request.state.context))
            else:
                res.append(validator(**request.state.context))
        res = [r for r in res if r]
        if len(res):
            raise RegTechHttpException(
                status_code=status.HTTP_403_FORBIDDEN,
                name=exception_name,
                detail=res,
            )

    return _run_validations
