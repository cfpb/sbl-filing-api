import logging

from sbl_filing_api.entities.models.dao import FilingPeriodDAO
from .base_validator import ActionValidator

log = logging.getLogger(__name__)


class CheckPeriodNotExists(ActionValidator):
    def __init__(self):
        super().__init__("check_period_not_exists")

    def __call__(self, period: FilingPeriodDAO, period_code: str, **kwargs):
        if not period:
            return f"The period ({period_code}) does not exist, therefore a Filing can not be created for this period."
