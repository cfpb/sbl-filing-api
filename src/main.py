import os

from fastapi import FastAPI

from routers import filing_router

from alembic.config import Config
from alembic import command

app = FastAPI()


@app.on_event("startup")
async def app_start():
    file_dir = os.path.dirname(os.path.realpath(__file__))
    alembic_cfg = Config(f"{file_dir}/../alembic.ini")
    alembic_cfg.set_main_option("script_location", f"{file_dir}/../db_revisions")
    alembic_cfg.set_main_option("prepend_sys_path", f"{file_dir}/../")
    command.upgrade(alembic_cfg, "head")


app.include_router(filing_router, prefix="/v1/filing")
