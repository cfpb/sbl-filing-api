import json

from io import BytesIO
from fastapi import BackgroundTasks, UploadFile
from regtech_data_validator.create_schemas import validate_phases
import pandas as pd
import importlib.metadata as imeta
from entities.models import SubmissionDAO, SubmissionState
from entities.repos.submission_repo import update_submission
from http import HTTPStatus
from fastapi import HTTPException
import logging
from fsspec import AbstractFileSystem, filesystem
from config import settings, FsProtocol

log = logging.getLogger(__name__)


def validate_file_processable(file: UploadFile) -> None:
    extension = file.filename.split(".")[-1].lower()
    if file.content_type != settings.submission_file_type or extension != settings.submission_file_extension:
        raise HTTPException(
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Only {settings.submission_file_type} file type with extension {settings.submission_file_extension} is supported; "
                f'submitted file is "{file.content_type}" with "{extension}" extension',
            ),
        )
    if file.size > settings.submission_file_size:
        raise HTTPException(
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded file size of {file.size} bytes exceeds the limit of {settings.submission_file_size} bytes.",
        )


async def upload_to_storage(lei: str, submission_id: str, content: bytes, extension: str = "csv"):
    try:
        fs: AbstractFileSystem = filesystem(settings.upload_fs_protocol.value)
        if settings.upload_fs_protocol == FsProtocol.FILE:
            fs.mkdirs(f"{settings.upload_fs_root}/{lei}", exist_ok=True)
        with fs.open(f"{settings.upload_fs_root}/{lei}/{submission_id}.{extension}", "wb") as f:
            f.write(content)
    except Exception as e:
        log.error("Failed to upload file", e, exc_info=True, stack_info=True)
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Failed to upload file")


async def validate_submission(lei: str, submission: SubmissionDAO, content: bytes, background_tasks: BackgroundTasks):
    df = pd.read_csv(BytesIO(content), dtype=str, na_filter=False)
    validator_version = imeta.version("regtech-data-validator")
    submission.state = SubmissionState.VALIDATION_IN_PROGRESS
    submission.validation_ruleset_version = validator_version
    # Set VALIDATION_IN_PROGRESS
    submission = await update_submission(submission)
    background_tasks.add_task(validate_and_update_submission, df, lei, submission)


async def validate_and_update_submission(df: pd.DataFrame, lei: str, submission: SubmissionDAO):
    # Validate Phases
    result = validate_phases(df, {"lei": lei})

    # Update tables with response
    if not result[0]:
        submission.state = (
            SubmissionState.VALIDATION_WITH_ERRORS
            if "error" in result[1]["validation_severity"].values
            else SubmissionState.VALIDATION_WITH_WARNINGS
        )
    else:
        submission.state = SubmissionState.VALIDATION_SUCCESSFUL
    submission.validation_json = json.loads(result[1].to_json())
    await update_submission(submission)
