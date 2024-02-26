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
    db_schema: str = "public"
    db_name: str
    db_user: str
    db_pwd: str
    db_host: str
    db_scheme: str = "postgresql+asyncpg"
    conn: PostgresDsn | None = None
    '''
    upload_fs_protocol: to be used with fsspec, and s3fs
    `file` is for local file system
    `s3` is for AWS S3
    '''
    upload_fs_protocol: str
    '''
    upload_fs_root: root of the upload folder in file system
    with `file` protocol, this can be any directory you specific (e.g. `../upload`)
    if using `s3` for the protocol, this should be the bucket name (e.g. `my-s3-bucket`)
    '''
    upload_fs_root: str

    def __init__(self, **data):
        super().__init__(**data)

    @field_validator("conn", mode="before")
    @classmethod
    def build_postgres_dsn(cls, postgres_dsn, info: ValidationInfo) -> Any:
        postgres_dsn = PostgresDsn.build(
            scheme=info.data.get("db_scheme"),
            username=info.data.get("db_user"),
            password=parse.quote(info.data.get("db_pwd"), safe=""),
            host=info.data.get("db_host"),
            path=info.data.get("db_name"),
        )
        return str(postgres_dsn)

    model_config = SettingsConfigDict(env_file=env_files_to_load, extra="allow")


settings = Settings()

kc_settings = KeycloakSettings(_env_file=env_files_to_load)
