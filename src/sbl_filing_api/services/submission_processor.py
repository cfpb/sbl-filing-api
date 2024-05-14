import ujson
from typing import Generator
import pandas as pd
import importlib.metadata as imeta
import logging

from io import BytesIO
from fastapi import UploadFile
from regtech_data_validator.create_schemas import validate_phases, ValidationPhase
from regtech_data_validator.data_formatters import df_to_json, df_to_download
from regtech_data_validator.checks import Severity
from sbl_filing_api.entities.engine.engine import SessionLocal
from sbl_filing_api.entities.models.dao import SubmissionDAO, SubmissionState
from sbl_filing_api.entities.repos.submission_repo import update_submission
from http import HTTPStatus
from sbl_filing_api.config import settings
from sbl_filing_api.services import file_handler
from regtech_api_commons.api.exceptions import RegTechHttpException

log = logging.getLogger(__name__)

REPORT_QUALIFIER = "_report"


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


def upload_to_storage(period_code: str, lei: str, file_identifier: str, content: bytes, extension: str = "csv") -> None:
    try:
        file_handler.upload(path=f"upload/{period_code}/{lei}/{file_identifier}.{extension}", content=content)
    except Exception as e:
        raise RegTechHttpException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, name="Upload Failure", detail="Failed to upload file"
        ) from e


def get_from_storage(period_code: str, lei: str, file_identifier: str, extension: str = "csv") -> Generator:
    try:
        return file_handler.download(f"upload/{period_code}/{lei}/{file_identifier}.{extension}")
    except Exception as e:
        raise RegTechHttpException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, name="Download Failure", detail="Failed to read file."
        ) from e


async def validate_and_update_submission(
    period_code: str, lei: str, submission: SubmissionDAO, content: bytes, exec_check: dict
):
    async with SessionLocal() as session:
        try:
            validator_version = imeta.version("regtech-data-validator")
            submission.validation_ruleset_version = validator_version
            submission.state = SubmissionState.VALIDATION_IN_PROGRESS
            submission = await update_submission(session, submission)

            df = pd.read_csv(BytesIO(content), dtype=str, na_filter=False)
            submission.total_records = len(df)

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

            submission.validation_results = build_validation_results(result)
            submission_report = df_to_download(result[1])
            upload_to_storage(
                period_code, lei, str(submission.id) + REPORT_QUALIFIER, submission_report.encode("utf-8")
            )

            if not exec_check["continue"]:
                log.warning(f"Submission {submission.id} is expired, will not be updating final state with results.")
                return

            await update_submission(session, submission)

        except RuntimeError as re:
            log.error("The file is malformed", re, exc_info=True, stack_info=True)
            submission.state = SubmissionState.SUBMISSION_UPLOAD_MALFORMED
            await update_submission(session, submission)

        except Exception as e:
            log.error(
                f"Validation for submission {submission.id} did not complete due to an unexpected error.",
                e,
                exc_info=True,
                stack_info=True,
            )
            submission.state = SubmissionState.VALIDATION_ERROR
            await update_submission(session, submission)


def build_validation_results(result):
    val_json = ujson.loads(df_to_json(result[1]))

    if result[2] == ValidationPhase.SYNTACTICAL.value:
        val_res = {"syntax_errors": {"count": len(val_json), "details": val_json}}
    else:
        errors_list = [e for e in val_json if e["validation"]["severity"] == Severity.ERROR.value]
        warnings_list = [w for w in val_json if w["validation"]["severity"] == Severity.WARNING.value]
        val_res = {
            "syntax_errors": {"count": 0, "details": []},
            "logic_errors": {"count": len(errors_list), "details": errors_list},
            "logic_warnings": {"count": len(warnings_list), "details": warnings_list},
        }

    return val_res
