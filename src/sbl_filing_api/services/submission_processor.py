import json
import asyncio

from io import BytesIO
from fastapi import UploadFile
from regtech_data_validator.create_schemas import validate_phases
from regtech_data_validator.data_formatters import df_to_json, df_to_download
from regtech_data_validator.checks import Severity
import pandas as pd
import importlib.metadata as imeta
from sbl_filing_api.entities.models.dao import SubmissionDAO, SubmissionState
from sbl_filing_api.entities.repos.submission_repo import update_submission
from http import HTTPStatus
import logging
from fsspec import AbstractFileSystem, filesystem
from sbl_filing_api.config import FsProtocol, settings
from regtech_api_commons.api.exceptions import RegTechHttpException
import boto3

log = logging.getLogger(__name__)

REPORT_QUALIFIER = "_report"


async def validation_monitor(period_code: str, lei: str, submission: SubmissionDAO, content: bytes):
    try:
        await asyncio.wait_for(
            validate_and_update_submission(period_code, lei, submission, content),
            timeout=settings.expired_submission_check_secs,
        )
    except asyncio.TimeoutError as te:
        log.warn(
            f"Validation for submission {submission.id} did not complete within the expected timeframe, will be set to VALIDATION_EXPIRED.",
            te,
            exc_info=True,
            stack_info=True,
        )
        submission.state = SubmissionState.VALIDATION_EXPIRED
        await update_submission(submission)


def validate_file_processable(file: UploadFile) -> None:
    extension = file.filename.split(".")[-1].lower()
    if file.content_type != settings.submission_file_type or extension != settings.submission_file_extension:
        raise RegTechHttpException(
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            name="Unsupported File Type",
            detail=(
                f"Only {settings.submission_file_type} file type with extension {settings.submission_file_extension} is supported; "
                f'submitted file is "{file.content_type}" with "{extension}" extension',
            ),
        )
    if file.size > settings.submission_file_size:
        raise RegTechHttpException(
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            name="File Too Large",
            detail=f"Uploaded file size of {file.size} bytes exceeds the limit of {settings.submission_file_size} bytes.",
        )


async def upload_to_storage(period_code: str, lei: str, file_identifier: str, content: bytes, extension: str = "csv"):
    try:
        if settings.fs_upload_config.protocol == FsProtocol.FILE:
            fs: AbstractFileSystem = filesystem(settings.fs_upload_config.protocol)
            fs.mkdirs(f"{settings.fs_upload_config.root}/upload/{period_code}/{lei}", exist_ok=True)
            with fs.open(
                f"{settings.fs_upload_config.root}/upload/{period_code}/{lei}/{file_identifier}.{extension}", "wb"
            ) as f:
                f.write(content)
        else:
            s3 = boto3.client("s3")
            r = s3.put_object(
                Bucket=settings.fs_upload_config.root,
                Key=f"upload/{period_code}/{lei}/{file_identifier}.{extension}",
                Body=content,
            )
            log.debug(
                "s3 upload response for lei: %s, period: %s file: %s, response: %s",
                lei,
                period_code,
                file_identifier,
                r,
            )
    except Exception as e:
        raise RegTechHttpException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, name="Upload Failure", detail="Failed to upload file"
        ) from e


async def get_from_storage(period_code: str, lei: str, file_identifier: str, extension: str = "csv"):
    try:
        fs: AbstractFileSystem = filesystem(**settings.fs_download_config.__dict__)
        file_path = f"{settings.fs_upload_config.root}/upload/{period_code}/{lei}/{file_identifier}.{extension}"
        with fs.open(file_path, "r") as f:
            return f.name
    except Exception as e:
        raise RegTechHttpException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, name="Download Failure", detail="Failed to read file."
        ) from e


async def validate_and_update_submission(period_code: str, lei: str, submission: SubmissionDAO, content: bytes):
    validator_version = imeta.version("regtech-data-validator")
    submission.validation_ruleset_version = validator_version
    submission.state = SubmissionState.VALIDATION_IN_PROGRESS
    submission = await update_submission(submission)

    try:
        df = pd.read_csv(BytesIO(content), dtype=str, na_filter=False)

        # Validate Phases
        result = validate_phases(df, {"lei": lei})

        # Update tables with response
        if not result[0]:
            submission.state = (
                SubmissionState.VALIDATION_WITH_ERRORS
                if Severity.ERROR.value in result[1]["validation_severity"].values
                else SubmissionState.VALIDATION_WITH_WARNINGS
            )
        else:
            submission.state = SubmissionState.VALIDATION_SUCCESSFUL
        submission.validation_json = json.loads(df_to_json(result[1]))
        submission_report = df_to_download(result[1])
        await upload_to_storage(
            period_code, lei, str(submission.id) + REPORT_QUALIFIER, submission_report.encode("utf-8")
        )
        await update_submission(submission)

    except RuntimeError as re:
        log.error("The file is malformed", re, exc_info=True, stack_info=True)
        submission.state = SubmissionState.SUBMISSION_UPLOAD_MALFORMED
        await update_submission(submission)

    except Exception as e:
        log.error(
            f"Validation for submission {submission.id} did not complete due to an unexpected error.",
            e,
            exc_info=True,
            stack_info=True,
        )
        submission.state = SubmissionState.VALIDATION_ERROR
        await update_submission(submission)
