from enum import StrEnum
import os
from urllib import parse
from typing import Any, Set

from pydantic import field_validator, ValidationInfo, BaseModel
from pydantic.networks import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from regtech_api_commons.oauth2.config import KeycloakSettings
from regtech_regex.regex_config import RegexConfigs

env_files_to_load = [".env"]
if os.getenv("ENV", "LOCAL") == "LOCAL":
    file_dir = os.path.dirname(os.path.realpath(__file__))
    env_files_to_load.append(f"{file_dir}/../.env.local")


class FsProtocol(StrEnum):
    FILE = "file"
    S3 = "s3"


class FsUploadConfig(BaseModel):
    protocol: str = FsProtocol.FILE.value
    root: str


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    """
    "workers" and "reload" are mutually exclusive, "workers" flag is ignored when reloading is enabled.
    """
    workers: int = 4
    reload: bool = False
    time_out: int = 65
    port: int = 8888
    log_config: str = "log-config.yml"


class Settings(BaseSettings):
    db_schema: str = "public"
    db_name: str
    db_user: str
    db_pwd: str
    db_host: str
    db_scheme: str = "postgresql+asyncpg"
    db_logging: bool = False
    conn: PostgresDsn | None = None

    fs_upload_config: FsUploadConfig

    server_config: ServerConfig = ServerConfig()

    submission_file_type: str = "text/csv"
    submission_file_extension: str = "csv"
    submission_file_size: int = 2 * (1024**3)

    expired_submission_check_secs: int = 120

    user_fi_api_url: str = "http://sbl-project-user_fi-1:8888/v1/institutions/"
    mail_api_url: str = "http://mail-api:8765/internal/confirmation/send"

    max_validation_errors: int = 1000000
    max_json_records: int = 10000
    max_json_group_size: int = 200

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

    model_config = SettingsConfigDict(env_file=env_files_to_load, extra="allow", env_nested_delimiter="__")


class RequestActionValidations(BaseSettings):
    sign_and_submit: Set[str] = {
        "valid_lei_status",
        "valid_lei_tin",
        "valid_filing_exists",
        "valid_sub_accepted",
        "valid_voluntary_filer",
        "valid_contact_info",
    }

    filing_create: Set[str] = {"valid_period_exists", "valid_no_filing_exists"}

    model_config = SettingsConfigDict(env_prefix="request_validators__", env_file=env_files_to_load, extra="allow")


settings = Settings()

request_action_validations = RequestActionValidations()

kc_settings = KeycloakSettings(_env_file=env_files_to_load)

regex_configs = RegexConfigs.instance()
