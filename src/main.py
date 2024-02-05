import os

from fastapi import FastAPI
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware

from regtech_api_commons.oauth2.oauth2_backend import BearerTokenAuthBackend
from regtech_api_commons.oauth2.oauth2_admin import OAuth2Admin

from routers import filing_router

from alembic.config import Config
from alembic import command

from config import kc_settings

app = FastAPI()


@app.on_event("startup")
async def app_start():
    file_dir = os.path.dirname(os.path.realpath(__file__))
    alembic_cfg = Config(f"{file_dir}/../alembic.ini")
    alembic_cfg.set_main_option("script_location", f"{file_dir}/../db_revisions")
    alembic_cfg.set_main_option("prepend_sys_path", f"{file_dir}/../")
    command.upgrade(alembic_cfg, "head")


token_bearer = OAuth2AuthorizationCodeBearer(
    authorizationUrl=kc_settings.auth_url.unicode_string(), tokenUrl=kc_settings.token_url.unicode_string()
)

app.add_middleware(AuthenticationMiddleware, backend=BearerTokenAuthBackend(token_bearer, OAuth2Admin(kc_settings)))
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["authorization"],
)


app.include_router(filing_router, prefix="/v1/filing")
