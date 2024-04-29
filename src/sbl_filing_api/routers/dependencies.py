import httpx
import os

from sbl_filing_api.config import settings
from http import HTTPStatus
from fastapi import Request
from regtech_api_commons.api.exceptions import RegTechHttpException


def verify_lei(request: Request, lei: str) -> None:
    res = httpx.get(settings.user_fi_api_url + lei, headers={"authorization": request.headers["authorization"]})
    lei_obj = res.json()
    if not lei_obj["is_active"]:
        raise RegTechHttpException(
            status_code=HTTPStatus.FORBIDDEN, name="Request Forbidden", detail=f"LEI {lei} is in an inactive state."
        )


def verify_user_lei_relation(request: Request, lei: str = None) -> None:
    if os.getenv("ENV", "LOCAL") != "LOCAL" and lei:
        if request.user.is_authenticated:
            institutions = request.user.institutions
            if lei not in institutions:
                raise RegTechHttpException(
                    status_code=HTTPStatus.FORBIDDEN,
                    name="Request Forbidden",
                    detail=f"LEI {lei} is not associated with the user.",
                )
