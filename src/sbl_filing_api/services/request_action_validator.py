import inspect
import logging
import httpx

from async_lru import alru_cache
from enum import StrEnum
from fastapi import Request, status
from http import HTTPStatus
from typing import Set

from regtech_api_commons.api.exceptions import RegTechHttpException

from sbl_filing_api.config import settings
from sbl_filing_api.entities.repos import submission_repo as repo
from sbl_filing_api.services.validators.base_validator import get_validation_registry

log = logging.getLogger(__name__)


class UserActionContext(StrEnum):
    FILING = "filing"
    INSTITUTION = "institution"
    PERIOD = "period"


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
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                settings.user_fi_api_url + fi_request.lei,
                headers={"authorization": fi_request.request.headers["authorization"]},
            )
            if res.status_code == HTTPStatus.OK:
                return res.json()
    except Exception:
        log.exception("Failed to retrieve fi data for %s", fi_request.lei)

    """
    `alru_cache` seems to cache `None` results, even though documentation for normal `lru_cache` seems to indicate it doesn't cache `None` by default.
    So manually invalidate the cache if no returnable result found
    """
    get_institution_data.cache_invalidate(fi_request)


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
        context = {"lei": lei, "period_code": period}
        if lei and UserActionContext.INSTITUTION in requirements:
            context = context | {UserActionContext.INSTITUTION: await get_institution_data(FiRequest(request, lei))}
        if period and UserActionContext.PERIOD in requirements:
            context = context | {
                UserActionContext.PERIOD: await repo.get_filing_period(request.state.db_session, period)
            }
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
        validation_registry = get_validation_registry()
        for validator_name in validator_names:
            validator = validation_registry.get(validator_name)
            if not validator:
                log.warning("Action validator [%s] not found.", validator_name)
            elif inspect.iscoroutinefunction(validator.__call__):
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
