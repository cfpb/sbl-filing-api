import inspect
import json
import logging
from enum import StrEnum
from typing import Any, Dict, List, Set

from async_lru import alru_cache
import httpx
from fastapi import Request, status
from pydantic_settings import BaseSettings
from regtech_api_commons.api.exceptions import RegTechHttpException

from sbl_filing_api.config import settings
from sbl_filing_api.entities.models.dao import FilingDAO, SubmissionDAO
from sbl_filing_api.entities.models.model_enums import SubmissionState, UserActionType
from sbl_filing_api.entities.repos import submission_repo as repo

log = logging.getLogger(__name__)


class UserActionContext(StrEnum):
    FILING = "filing"
    INSTITUTION = "institution"


# class RequestActionValidationSettings(BaseSettings):
#     check_lei_status: bool = True
#     check_lei_tin: bool = True
#     check_filing_exists: bool = True
#     check_sub_accepted: bool = True
#     check_voluntary_filer: bool = True
#     check_contact_info: bool = True


@alru_cache(ttl=60*60)
async def get_institution_data(request: Request, lei: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(settings.user_fi_api_url + lei, headers={"authorization": request.headers["authorization"]})
        return res.json()


def check_lei_status(institution: Dict[str, Any], **kwargs):
    try:
        is_active = institution["lei_status"]["can_file"]
        if not is_active:
            return f"LEI status of {institution['lei_status_code']} cannot file."
    except Exception:
        log.exception("Unable to determine lei status: %s", json.dumps(institution))
        return "Unable to determine LEI status."


def check_lei_tin(institution: Dict[str, Any], **kwargs):
    if not institution["tax_id"]:
        return "TIN is required to file"


def check_filing_exists(filing: FilingDAO, lei: str, period: str, **kwargs):
    if not filing:
        return f"There is no Filing for LEI {lei} in period {period}, unable to sign a non-existent Filing."


async def check_sub_accepted(filing: FilingDAO, **kwargs):
    submissions: List[SubmissionDAO] = await filing.awaitable_attrs.submissions
    if not len(submissions) or submissions[0].state != SubmissionState.SUBMISSION_ACCEPTED:
        filing.lei
        filing.filing_period
        return f"Cannot sign filing. Filing for {filing.lei} for period {filing.filing_period} does not have a latest submission the SUBMISSION_ACCEPTED state."


def check_voluntary_filer(filing: FilingDAO, **kwargs):
    if filing.is_voluntary is None:
        return f"Cannot sign filing. Filing for {filing.lei} for period {filing.period} does not have a selection of is_voluntary defined."


def check_contact_info(filing: FilingDAO, **kwargs):
    if not filing.contact_info:
        return f"Cannot sign filing. Filing for {filing.lei} for period {filing.period} does not have contact info defined."


user_action_validation_registry = {
    UserActionType.SIGN: {
        check_lei_status,
        check_lei_tin,
        check_filing_exists,
        check_sub_accepted,
        check_voluntary_filer,
        check_contact_info,
    }
}


def set_context(requirements: Set[UserActionContext]):
    async def _set_context(request: Request):
        lei = request.path_params.get("lei")
        period = request.path_params.get("period_code")
        context = {"lei": lei, "period": period}
        if lei and UserActionContext.INSTITUTION in requirements:
            context = context | {UserActionContext.INSTITUTION: await get_institution_data(request, lei)}
        if period and UserActionContext.FILING in requirements:
            context = context | {UserActionContext.FILING: await repo.get_filing(request.state.db_session, lei, period)}
        request.state.context = context

    return _set_context


def validate_user_action(types: Set[str]):
    async def _run_validations(request: Request):
        res = []
        for type in types:
            checkers = user_action_validation_registry[type]
            for checker in checkers:
                if inspect.iscoroutinefunction(checker):
                    res.append(await checker(**request.state.context))
                else:
                    res.append(checker(**request.state.context))
        res = [r for r in res if r]
        if len(res):
            raise RegTechHttpException(
                status_code=status.HTTP_403_FORBIDDEN,
                name="Filing Action Forbidden",
                detail=res,
            )

    return _run_validations
