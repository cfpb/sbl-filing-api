import logging

from typing import List

from sbl_filing_api.entities.models.dao import FilingDAO, SubmissionDAO
from sbl_filing_api.entities.models.model_enums import SubmissionState
from .base_validator import ActionValidator

log = logging.getLogger(__name__)


class ValidSubAccepted(ActionValidator):
    def __init__(self):
        super().__init__("valid_sub_accepted")

    def __call__(self, filing: FilingDAO, **kwargs):
        if filing:
            submissions: List[SubmissionDAO] = filing.submissions
            if not len(submissions) or submissions[0].state != SubmissionState.SUBMISSION_ACCEPTED:
                return f"Cannot sign filing. Filing for {filing.lei} for period {filing.filing_period} does not have a latest submission in the SUBMISSION_ACCEPTED state."
