import json
import logging

from typing import Any, Dict

from .base_validator import ActionValidator

log = logging.getLogger(__name__)


class ValidLeiStatus(ActionValidator):
    def __init__(self):
        super().__init__("valid_lei_status")

    def __call__(self, institution: Dict[str, Any], **kwargs):
        try:
            is_active = institution["lei_status"]["can_file"]
            if not is_active:
                return f"Cannot sign filing. LEI status of {institution['lei_status_code']} cannot file."
        except Exception:
            log.exception("Unable to determine lei status: %s", json.dumps(institution))
            return "Unable to determine LEI status."


class ValidLeiTin(ActionValidator):
    def __init__(self):
        super().__init__("valid_lei_tin")

    def __call__(self, institution: Dict[str, Any], **kwargs):
        if not (institution and institution.get("tax_id")):
            return "Cannot sign filing. TIN is required to file."
