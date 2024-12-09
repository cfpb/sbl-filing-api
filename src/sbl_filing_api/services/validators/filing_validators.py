import logging

from sbl_filing_api.entities.models.dao import FilingPeriodDAO, FilingDAO
from .base_validator import ActionValidator

log = logging.getLogger(__name__)


class CheckPeriodExists(ActionValidator):
    def __init__(self):
        super().__init__("check_period_exists")

    def __call__(self, period: FilingPeriodDAO, period_code: str, **kwargs):
        if not period:
            return f"The period ({period_code}) does not exist, therefore a Filing can not be created for this period."


class CheckPeriodFilingExists(ActionValidator):
    def __init__(self):
        super().__init__("check_period_filing_exists")

    def __call__(self, filing: FilingDAO, period_code: str, lei: str, **kwargs):
        if filing:
            return f"Filing already exists for Filing Period {period_code} and LEI {lei}"
