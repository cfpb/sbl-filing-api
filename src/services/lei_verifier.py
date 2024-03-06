import httpx

from config import settings
from http import HTTPStatus
from fastapi import Request, HTTPException


def verify_lei(request: Request, lei: str) -> None:
    res = httpx.get(settings.user_fi_api_url + lei, headers={"authorization": request.headers["authorization"]})
    lei_obj = res.json()
    if not lei_obj["is_active"]:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=f"LEI {lei} is in an inactive state.")
