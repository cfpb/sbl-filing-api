import logging

from typing import List

from sbl_filing_api.entities.models.dao import FilingDAO, SubmissionDAO
from sbl_filing_api.entities.models.model_enums import SubmissionState
from .base_validator import ActionValidator

log = logging.getLogger(__name__)


class ValidSubAccepted(ActionValidator):
    def __init__(self):
        super().__init__("valid_sub_accepted")

    async def __call__(self, filing: FilingDAO, **kwargs):
        if filing:
            submissions: List[SubmissionDAO] = await filing.awaitable_attrs.submissions
            if not len(submissions) or submissions[0].state != SubmissionState.SUBMISSION_ACCEPTED:
                filing.lei
                filing.filing_period
                return f"Cannot sign filing. Filing for {filing.lei} for period {filing.filing_period} does not have a latest submission in the SUBMISSION_ACCEPTED state."
