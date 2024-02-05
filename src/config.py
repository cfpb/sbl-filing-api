import os
from urllib import parse
from typing import Any

from pydantic import field_validator, ValidationInfo
from pydantic.networks import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from regtech_api_commons.oauth2.config import KeycloakSettings

env_files_to_load = [".env"]
if os.getenv("ENV", "LOCAL") == "LOCAL":
    env_files_to_load.append(".env.local")


class Settings(BaseSettings):
    inst_db_schema: str = "public"
    inst_db_name: str
    inst_db_user: str
    inst_db_pwd: str
    inst_db_host: str
    inst_db_scheme: str = "postgresql+asyncpg"
    inst_conn: PostgresDsn | None = None

    def __init__(self, **data):
        super().__init__(**data)

    @field_validator("inst_conn", mode="before")
    @classmethod
    def build_postgres_dsn(cls, postgres_dsn, info: ValidationInfo) -> Any:
        postgres_dsn = PostgresDsn.build(
            scheme=info.data.get("inst_db_scheme"),
            username=info.data.get("inst_db_user"),
            password=parse.quote(info.data.get("inst_db_pwd"), safe=""),
            host=info.data.get("inst_db_host"),
            path=info.data.get("inst_db_name"),
        )
        return str(postgres_dsn)

    model_config = SettingsConfigDict(env_file=env_files_to_load, extra="allow")


settings = Settings()

kc_settings = KeycloakSettings(_env_file=env_files_to_load)
