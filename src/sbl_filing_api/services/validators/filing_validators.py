import logging

from sbl_filing_api.entities.models.dao import FilingDAO
from sbl_filing_api.entities.models.model_enums import FilingState
from .base_validator import ActionValidator

log = logging.getLogger(__name__)


class ValidNoFilingExists(ActionValidator):
    def __init__(self):
        super().__init__("valid_no_filing_exists")

    def __call__(self, filing: FilingDAO, period_code: str, lei: str, **kwargs):
        if filing:
            return f"Filing already exists for Filing Period {period_code} and LEI {lei}"


class ValidFilingExistsSign(ActionValidator):
    def __init__(self):
        super().__init__("valid_filing_exists_sign")

    def __call__(self, filing: FilingDAO, lei: str, period_code: str, **kwargs):
        if not filing:
            return f"There is no Filing for LEI {lei} in period {period_code}, unable to sign a non-existent Filing."


class ValidFilingExistsReopen(ActionValidator):
    def __init__(self):
        super().__init__("valid_filing_exists_reopen")

    def __call__(self, filing: FilingDAO, lei: str, period_code: str, **kwargs):
        if not filing:
            return f"There is no Filing for LEI {lei} in period {period_code}, unable to reopen a non-existent Filing."


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


class ValidFilingOpen(ActionValidator):
    def __init__(self):
        super().__init__("valid_filing_open")

    def __call__(self, *args, filing: FilingDAO, **kwargs):
        if filing and filing.state is FilingState.CLOSED:
            return f"Cannot sign filing. Filing state for {filing.lei} for period {filing.filing_period} is CLOSED."


class ValidFilingNotOpen(ActionValidator):
    def __init__(self):
        super().__init__("valid_filing_not_open")

    def __call__(self, *args, filing: FilingDAO, **kwargs):
        if filing and filing.state is FilingState.OPEN:
            return f"Cannot reopen filing. Filing state for {filing.lei} for period {filing.filing_period} is OPEN."
