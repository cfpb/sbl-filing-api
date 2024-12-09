import json
import logging

from typing import Any, Dict, List

from sbl_filing_api.entities.models.dao import FilingDAO, SubmissionDAO
from sbl_filing_api.entities.models.model_enums import SubmissionState
from .base_validator import ActionValidator

log = logging.getLogger(__name__)


class CheckLeiStatus(ActionValidator):
    def __init__(self):
        super().__init__("check_lei_status")

    def __call__(self, institution: Dict[str, Any], **kwargs):
        try:
            is_active = institution["lei_status"]["can_file"]
            if not is_active:
                return f"Cannot sign filing. LEI status of {institution['lei_status_code']} cannot file."
        except Exception:
            log.exception("Unable to determine lei status: %s", json.dumps(institution))
            return "Unable to determine LEI status."


class CheckLeiTin(ActionValidator):
    def __init__(self):
        super().__init__("check_lei_tin")

    def __call__(self, institution: Dict[str, Any], **kwargs):
        if not (institution and institution.get("tax_id")):
            return "Cannot sign filing. TIN is required to file."


class CheckFilingExists(ActionValidator):
    def __init__(self):
        super().__init__("check_filing_exists")

    def __call__(self, filing: FilingDAO, lei: str, period_code: str, **kwargs):
        if not filing:
            return f"There is no Filing for LEI {lei} in period {period_code}, unable to sign a non-existent Filing."


class CheckSubAccepted(ActionValidator):
    def __init__(self):
        super().__init__("check_sub_accepted")

    async def __call__(self, filing: FilingDAO, **kwargs):
        if filing:
            submissions: List[SubmissionDAO] = await filing.awaitable_attrs.submissions
            if not len(submissions) or submissions[0].state != SubmissionState.SUBMISSION_ACCEPTED:
                filing.lei
                filing.filing_period
                return f"Cannot sign filing. Filing for {filing.lei} for period {filing.filing_period} does not have a latest submission in the SUBMISSION_ACCEPTED state."


class CheckVoluntaryFiler(ActionValidator):
    def __init__(self):
        super().__init__("check_voluntary_filer")

    def __call__(self, filing: FilingDAO, **kwargs):
        if filing and filing.is_voluntary is None:
            return f"Cannot sign filing. Filing for {filing.lei} for period {filing.filing_period} does not have a selection of is_voluntary defined."


class CheckContactInfo(ActionValidator):
    def __init__(self):
        super().__init__("check_contact_info")

    def __call__(self, filing: FilingDAO, **kwargs):
        if filing and not filing.contact_info:
            return f"Cannot sign filing. Filing for {filing.lei} for period {filing.filing_period} does not have contact info defined."
