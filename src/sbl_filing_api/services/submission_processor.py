from typing import Generator
import polars as pl
import importlib.metadata as imeta
import logging

from fastapi import UploadFile
from regtech_data_validator.validator import validate_batch_csv
from regtech_data_validator.data_formatters import df_to_dicts, df_to_download
from regtech_data_validator.checks import Severity
from regtech_data_validator.validation_results import ValidationPhase
from sbl_filing_api.entities.engine.engine import SessionLocal
from sbl_filing_api.entities.models.dao import SubmissionDAO, SubmissionState
from sbl_filing_api.entities.repos.submission_repo import update_submission
from http import HTTPStatus
from sbl_filing_api.config import FsProtocol, settings
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


def generate_file_path(period_code: str, lei: str, file_identifier: str, extension: str = "csv"):
    file_path = f"{settings.fs_upload_config.root}/upload/{period_code}/{lei}/{file_identifier}.{extension}"
    if settings.fs_upload_config.protocol == FsProtocol.S3.value:
        file_path = "s3://" + file_path
    return file_path


async def validate_and_update_submission(
    period_code: str, lei: str, submission: SubmissionDAO, content: bytes, exec_check: dict
):
    async with SessionLocal() as session:
        try:
            validator_version = imeta.version("regtech-data-validator")
            submission.validation_ruleset_version = validator_version
            submission.state = SubmissionState.VALIDATION_IN_PROGRESS
            submission = await update_submission(session, submission)

            final_phase = ValidationPhase.LOGICAL
            all_findings = []
            final_df = pl.DataFrame()

            file_path = generate_file_path(period_code, lei, submission.id)
            for findings, phase in validate_batch_csv(file_path, context={"lei": lei}, batch_size=50000, batch_count=5):
                final_phase = phase
                all_findings.append(findings)

            if all_findings:
                final_df = pl.concat(all_findings, how="diagonal")

            submission.validation_results = build_validation_results(final_df, final_phase)

            if not all_findings:
                submission.state = SubmissionState.VALIDATION_SUCCESSFUL
            else:
                submission.state = (
                    SubmissionState.VALIDATION_WITH_ERRORS
                    if final_df.filter(pl.col("validation_type") == Severity.ERROR).height > 0
                    else SubmissionState.VALIDATION_WITH_WARNINGS
                )

            report_path = generate_file_path(period_code, lei, f"{submission.id}_report")
            log.info(f"Writing csv report to {report_path}")
            df_to_download(final_df, report_path)
            # upload_to_storage(
            #    period_code, lei, str(submission.id) + REPORT_QUALIFIER, submission_report.encode("utf-8")
            # )
            if not exec_check["continue"]:
                log.warning(f"Submission {submission.id} is expired, will not be updating final state with results.")
                return

            await update_submission(session, submission)

        except RuntimeError as re:
            log.exception("The file is malformed.", re)
            submission.state = SubmissionState.SUBMISSION_UPLOAD_MALFORMED
            await update_submission(session, submission)

        except Exception as e:
            log.exception("Validation for submission %d did not complete due to an unexpected error.", submission.id, e)
            submission.state = SubmissionState.VALIDATION_ERROR
            await update_submission(session, submission)


def build_validation_results(findings: pl.DataFrame, phase: ValidationPhase):
    val_json = df_to_dicts(findings, settings.max_json_records, settings.max_json_group_size)
    if phase == ValidationPhase.SYNTACTICAL:
        findings_count = findings.filter(
            pl.col("validation_type") == Severity.ERROR, pl.col("scope") == "single-field"
        ).height
        val_res = {
            "syntax_errors": {
                "single_field_count": findings_count,
                "multi_field_count": 0,  # this will always be zero for syntax errors
                "register_count": 0,  # this will always be zero for syntax errors
                "total_count": findings_count,
                "details": val_json,
            }
        }
    else:
        # The findings dataframe might not have any columns if there were no findings/check violations
        # so build out the json structure as empty results first, then populate values if there is at least
        # one finding
        errors_list = [e for e in val_json if e["validation"]["severity"] == Severity.ERROR]
        warnings_list = [w for w in val_json if w["validation"]["severity"] == Severity.WARNING]
        val_res = {
            "syntax_errors": {
                "single_field_count": 0,
                "multi_field_count": 0,
                "register_count": 0,
                "total_count": 0,
                "details": [],
            },
            "logic_errors": {
                "single_field_count": 0,
                "multi_field_count": 0,
                "register_count": 0,
                "total_count": 0,
                "details": [],
            },
            "logic_warnings": {
                "single_field_count": 0,
                "multi_field_count": 0,
                "register_count": 0,
                "total_count": 0,
                "details": [],
            },
        }

        if not findings.is_empty():
            val_res["logic_errors"]["single_field_count"] = findings.filter(
                pl.col("validation_type") == Severity.ERROR, pl.col("scope") == "single-field"
            ).height
            val_res["logic_errors"]["multi_field_count"] = findings.filter(
                pl.col("validation_type") == Severity.ERROR, pl.col("scope") == "multi-field"
            ).height
            val_res["logic_errors"]["register_count"] = findings.filter(
                pl.col("validation_type") == Severity.ERROR, pl.col("scope") == "register"
            ).height
            val_res["logic_errors"]["total_count"] = (
                findings.filter(pl.col("validation_type") == Severity.ERROR).height,
            )
            val_res["logic_errors"]["details"] = errors_list

            val_res["logic_warnings"]["single_field_count"] = findings.filter(
                pl.col("validation_type") == Severity.WARNING, pl.col("scope") == "single-field"
            ).height
            val_res["logic_warnings"]["multi_field_count"] = findings.filter(
                pl.col("validation_type") == Severity.WARNING, pl.col("scope") == "multi-field"
            ).height
            val_res["logic_warnings"]["register_count"] = findings.filter(
                pl.col("validation_type") == Severity.WARNING, pl.col("scope") == "register"
            ).height
            val_res["logic_warnings"]["total_count"] = (
                findings.filter(pl.col("validation_type") == Severity.WARNING).height,
            )
            val_res["logic_warnings"]["details"] = warnings_list

    return val_res
