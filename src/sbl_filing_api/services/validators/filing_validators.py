import logging

from sbl_filing_api.entities.models.dao import FilingDAO
from .base_validator import ActionValidator

log = logging.getLogger(__name__)


class ValidNoFilingExists(ActionValidator):
    def __init__(self):
        super().__init__("valid_no_filing_exists")

    def __call__(self, filing: FilingDAO, period_code: str, lei: str, **kwargs):
        if filing:
            return f"Filing already exists for Filing Period {period_code} and LEI {lei}"


class ValidFilingExists(ActionValidator):
    def __init__(self):
        super().__init__("valid_filing_exists")

    def __call__(self, filing: FilingDAO, lei: str, period_code: str, **kwargs):
        if not filing:
            return f"There is no Filing for LEI {lei} in period {period_code}, unable to sign a non-existent Filing."


class ValidVoluntaryFiler(ActionValidator):
    def __init__(self):
        super().__init__("valid_voluntary_filer")

    def __call__(self, filing: FilingDAO, **kwargs):
        if filing and filing.is_voluntary is None:
            return f"Cannot sign filing. Filing for {filing.lei} for period {filing.filing_period} does not have a selection of is_voluntary defined."


class ValidContactInfo(ActionValidator):
    def __init__(self):
        super().__init__("valid_contact_info")

    def __call__(self, filing: FilingDAO, **kwargs):
        if filing and not filing.contact_info:
            return f"Cannot sign filing. Filing for {filing.lei} for period {filing.filing_period} does not have contact info defined."
