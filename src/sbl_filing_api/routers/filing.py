import asyncio
import logging
import csv
import io

from concurrent.futures import ProcessPoolExecutor
from fastapi import Depends, Request, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from multiprocessing import Manager
from regtech_api_commons.api.router_wrapper import Router
from regtech_api_commons.api.exceptions import RegTechHttpException
from regtech_api_commons.models.auth import AuthenticatedUser

from sbl_filing_api.entities.models.dao import FilingDAO
from sbl_filing_api.entities.models.model_enums import UserActionType
from sbl_filing_api.services import submission_processor
from sbl_filing_api.services.multithread_handler import handle_submission
from sbl_filing_api.config import request_action_validations
from typing import Annotated, List

from sbl_filing_api.entities.engine.engine import get_session
from sbl_filing_api.entities.models.dto import (
    FilingPeriodDTO,
    SubmissionDTO,
    FilingDTO,
    SnapshotUpdateDTO,
    StateUpdateDTO,
    ContactInfoDTO,
    SubmissionState,
    UserActionDTO,
    VoluntaryUpdateDTO,
)

from sbl_filing_api.entities.repos import submission_repo as repo

from sqlalchemy.ext.asyncio import AsyncSession

from starlette.authentication import requires

from regtech_api_commons.api.dependencies import verify_user_lei_relation

from sbl_filing_api.services.request_handler import send_confirmation_email

from sbl_filing_api.services.request_action_validator import UserActionContext, validate_user_action, set_context

logger = logging.getLogger(__name__)


async def set_db(request: Request, session: Annotated[AsyncSession, Depends(get_session)]):
    request.state.db_session = session


executor = ProcessPoolExecutor()
router = Router(dependencies=[Depends(set_db), Depends(verify_user_lei_relation)])


@router.get("/periods", response_model=List[FilingPeriodDTO])
@requires("authenticated")
async def get_filing_periods(request: Request):
    return await repo.get_filing_periods(request.state.db_session)


@router.get("/institutions/{lei}/filings/{period_code}", response_model=FilingDTO | None)
@requires("authenticated")
async def get_filing(request: Request, response: Response, lei: str, period_code: str):
    res = await repo.get_filing(request.state.db_session, lei, period_code)
    if res:
        return res
    response.status_code = status.HTTP_204_NO_CONTENT


@router.get("/periods/{period_code}/filings", response_model=List[FilingDTO])
@requires("authenticated")
async def get_filings(request: Request, period_code: str):
    user: AuthenticatedUser = request.user
    return await repo.get_filings(request.state.db_session, user.institutions, period_code)


@router.post(
    "/institutions/{lei}/filings/{period_code}",
    response_model=FilingDTO,
    dependencies=[
        Depends(set_context({UserActionContext.PERIOD, UserActionContext.FILING})),
        Depends(validate_user_action(request_action_validations.filing_create, "Filing Create Forbidden")),
    ],
)
@requires("authenticated")
async def post_filing(request: Request, lei: str, period_code: str):
    creator = None
    try:
        creator = await repo.add_user_action(
            request.state.db_session,
            UserActionDTO(
                user_id=request.user.id,
                user_name=request.user.name,
                user_email=request.user.email,
                action_type=UserActionType.CREATE,
            ),
        )
    except Exception:
        logger.exception("Error while trying to create the filing.creator UserAction.")
        raise RegTechHttpException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            name="Filing.creator UserAction error",
            detail="Error while trying to create the filing.creator UserAction.",
        )

    try:
        return await repo.create_new_filing(request.state.db_session, lei, period_code, creator_id=creator.id)
    except Exception:
        raise RegTechHttpException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            name="Filing Creation Error",
            detail=f"An error occurred while creating a filing for LEI {lei} and Filing Period {period_code}.",
        )


@router.put(
    "/institutions/{lei}/filings/{period_code}/sign",
    response_model=FilingDTO,
    dependencies=[
        Depends(set_context({UserActionContext.INSTITUTION, UserActionContext.FILING})),
        Depends(validate_user_action(request_action_validations.sign_and_submit, "Filing Action Forbidden")),
    ],
)
@requires("authenticated")
async def sign_filing(request: Request, lei: str, period_code: str):
    filing: FilingDAO = request.state.context["filing"]
    latest_sub = (await filing.awaitable_attrs.submissions)[0]
    sig = await repo.add_user_action(
        request.state.db_session,
        UserActionDTO(
            user_id=request.user.id,
            user_name=request.user.name,
            user_email=request.user.email,
            action_type=UserActionType.SIGN,
        ),
    )
    sig_timestamp = int(sig.timestamp.timestamp())
    filing.confirmation_id = lei + "-" + period_code + "-" + str(latest_sub.counter) + "-" + str(sig_timestamp)
    filing.signatures.append(sig)
    send_confirmation_email(
        request.user.name, request.user.email, filing.contact_info.email, filing.confirmation_id, sig_timestamp
    )
    return await repo.upsert_filing(request.state.db_session, filing)


@router.post("/institutions/{lei}/filings/{period_code}/submissions", response_model=SubmissionDTO)
@requires("authenticated")
async def upload_file(request: Request, lei: str, period_code: str, file: UploadFile):
    submission_processor.validate_file_processable(file)
    content = await file.read()

    filing = await repo.get_filing(request.state.db_session, lei, period_code)
    if not filing:
        raise RegTechHttpException(
            status_code=status.HTTP_404_NOT_FOUND,
            name="Filing Not Found",
            detail=f"There is no Filing for LEI {lei} in period {period_code}, unable to submit file.",
        )
    submission = None
    try:
        submitter = await repo.add_user_action(
            request.state.db_session,
            UserActionDTO(
                user_id=request.user.id,
                user_name=request.user.name,
                user_email=request.user.email,
                action_type=UserActionType.SUBMIT,
            ),
        )
        submission = await repo.add_submission(request.state.db_session, filing.id, file.filename, submitter.id)
        try:
            submission_processor.upload_to_storage(
                period_code, lei, submission.counter, content, file.filename.split(".")[-1]
            )

            submission.state = SubmissionState.SUBMISSION_UPLOADED
            with io.BytesIO(content) as byte_stream:
                reader = csv.reader(io.TextIOWrapper(byte_stream))
                submission.total_records = sum(1 for row in reader) - 1
            submission = await repo.update_submission(request.state.db_session, submission)
        except Exception as e:
            submission.state = SubmissionState.UPLOAD_FAILED
            submission = await repo.update_submission(request.state.db_session, submission)
            raise RegTechHttpException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                name="Submission Unprocessable",
                detail=f"Error while trying to process Submission {submission.id}",
            ) from e

        exec_check = Manager().dict()
        exec_check["continue"] = True
        loop = asyncio.get_event_loop()
        loop.run_in_executor(executor, handle_submission, period_code, lei, submission, content, exec_check)

        return submission

    except Exception as e:
        if submission:
            try:
                submission.state = SubmissionState.UPLOAD_FAILED
                submission = await repo.update_submission(request.state.db_session, submission)
            except Exception as ex:
                logger.error(
                    (
                        f"Error updating submission {submission.id} to {SubmissionState.UPLOAD_FAILED} state during error handling,"
                        f" the submission may be stuck in the {SubmissionState.SUBMISSION_STARTED} or {SubmissionState.SUBMISSION_UPLOADED} state."
                    ),
                    ex,
                    exc_info=True,
                    stack_info=True,
                )
        raise RegTechHttpException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            name="Submission Unprocessable",
            detail="Error while trying to process SUBMIT User Action",
        ) from e


@router.get("/institutions/{lei}/filings/{period_code}/submissions", response_model=List[SubmissionDTO])
@requires("authenticated")
async def get_submissions(request: Request, lei: str, period_code: str):
    return await repo.get_submissions(request.state.db_session, lei, period_code)


@router.get("/institutions/{lei}/filings/{period_code}/submissions/latest", response_model=SubmissionDTO)
@requires("authenticated")
async def get_submission_latest(request: Request, lei: str, period_code: str):
    filing = await repo.get_filing(request.state.db_session, lei, period_code)
    if not filing:
        raise RegTechHttpException(
            status_code=status.HTTP_404_NOT_FOUND,
            name="Filing Not Found",
            detail=f"There is no Filing for LEI {lei} in period {period_code}, unable to get latest submission for it.",
        )
    result = await repo.get_latest_submission(request.state.db_session, lei, period_code)
    if result:
        return result
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/institutions/{lei}/filings/{period_code}/submissions/{counter}", response_model=SubmissionDTO | None)
@requires("authenticated")
async def get_submission(request: Request, response: Response, counter: int, lei: str, period_code: str):
    result = await repo.get_submission_by_counter(request.state.db_session, lei, period_code, counter)
    if result:
        return result
    response.status_code = status.HTTP_404_NOT_FOUND


@router.put("/institutions/{lei}/filings/{period_code}/submissions/{counter}/accept", response_model=SubmissionDTO)
@requires("authenticated")
async def accept_submission(request: Request, counter: int, lei: str, period_code: str):
    submission = await repo.get_submission_by_counter(request.state.db_session, lei, period_code, counter)
    if not submission:
        raise RegTechHttpException(
            status_code=status.HTTP_404_NOT_FOUND,
            name="Submission Not Found",
            detail=f"Submission {counter} for LEI {lei} in filing period {period_code} does not exist, cannot accept a non-existing submission.",
        )
    if (
        submission.state != SubmissionState.VALIDATION_SUCCESSFUL
        and submission.state != SubmissionState.VALIDATION_WITH_WARNINGS
    ):
        raise RegTechHttpException(
            status_code=status.HTTP_403_FORBIDDEN,
            name="Submission Action Forbidden",
            detail=f"Submission {counter} for LEI {lei} in filing period {period_code} is not in an acceptable state.  Submissions must be validated successfully or with only warnings to be accepted.",
        )

    accepter = await repo.add_user_action(
        request.state.db_session,
        UserActionDTO(
            user_id=request.user.id,
            user_name=request.user.name,
            user_email=request.user.email,
            action_type=UserActionType.ACCEPT,
        ),
    )

    submission.accepter_id = accepter.id
    submission.state = SubmissionState.SUBMISSION_ACCEPTED
    submission = await repo.update_submission(request.state.db_session, submission)
    return submission


@router.put("/institutions/{lei}/filings/{period_code}/institution-snapshot-id", response_model=FilingDTO)
@requires("authenticated")
async def put_institution_snapshot(request: Request, lei: str, period_code: str, update_value: SnapshotUpdateDTO):
    result = await repo.get_filing(request.state.db_session, lei, period_code)
    if result:
        result.institution_snapshot_id = update_value.institution_snapshot_id
        return await repo.upsert_filing(request.state.db_session, result)
    raise RegTechHttpException(
        status_code=status.HTTP_404_NOT_FOUND,
        name="Filing Not Found",
        detail=f"A Filing for the LEI ({lei}) and period ({period_code}) that was attempted to be updated does not exist.",
    )


@router.post("/institutions/{lei}/filings/{period_code}/tasks/{task_name}", deprecated=True)
@requires("authenticated")
async def update_task_state(request: Request, lei: str, period_code: str, task_name: str, state: StateUpdateDTO):
    await repo.update_task_state(request.state.db_session, lei, period_code, task_name, state.state, request.user)


@router.get("/institutions/{lei}/filings/{period_code}/contact-info", response_model=ContactInfoDTO | None)
@requires("authenticated")
async def get_contact_info(request: Request, response: Response, lei: str, period_code: str):
    filing = await repo.get_filing(request.state.db_session, lei, period_code)
    if filing and filing.contact_info:
        return filing.contact_info
    response.status_code = status.HTTP_404_NOT_FOUND


@router.put("/institutions/{lei}/filings/{period_code}/contact-info", response_model=FilingDTO)
@requires("authenticated")
async def put_contact_info(request: Request, lei: str, period_code: str, contact_info: ContactInfoDTO):
    result = await repo.get_filing(request.state.db_session, lei, period_code)
    if result:
        return await repo.update_contact_info(request.state.db_session, lei, period_code, contact_info)
    raise RegTechHttpException(
        status_code=status.HTTP_404_NOT_FOUND,
        name="Filing Not Found",
        detail=f"A Filing for the LEI ({lei}) and period ({period_code}) that was attempted to be updated does not exist.",
    )


@router.get(
    "/institutions/{lei}/filings/{period_code}/submissions/latest/report",
    responses={200: {"content": {"text/plain; charset=utf-8": {}}}},
)
@requires("authenticated")
async def get_latest_submission_report(request: Request, lei: str, period_code: str):
    filing = await repo.get_filing(request.state.db_session, lei, period_code)
    if not filing:
        raise RegTechHttpException(
            status_code=status.HTTP_404_NOT_FOUND,
            name="Filing Not Found",
            detail=f"There is no Filing for LEI {lei} in period {period_code}, unable to get latest submission for it.",
        )
    latest_sub = await repo.get_latest_submission(request.state.db_session, lei, period_code)
    if latest_sub and latest_sub.state in [
        SubmissionState.VALIDATION_SUCCESSFUL,
        SubmissionState.VALIDATION_WITH_ERRORS,
        SubmissionState.VALIDATION_WITH_WARNINGS,
        SubmissionState.SUBMISSION_ACCEPTED,
    ]:
        file_data = submission_processor.get_from_storage(
            period_code, lei, str(latest_sub.counter) + submission_processor.REPORT_QUALIFIER
        )
        return StreamingResponse(
            content=file_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{latest_sub.counter}_validation_report.csv"',
                "Cache-Control": "no-store",
            },
        )
    else:
        raise RegTechHttpException(
            status_code=status.HTTP_404_NOT_FOUND,
            name="Report Not Found",
            detail=f"Report for ({filing.id}) does not exist.",
        )


@router.get(
    "/institutions/{lei}/filings/{period_code}/submissions/{counter}/report",
    responses={200: {"content": {"text/plain; charset=utf-8": {}}}},
)
@requires("authenticated")
async def get_submission_report(request: Request, response: Response, lei: str, period_code: str, counter: int):
    sub = await repo.get_submission_by_counter(request.state.db_session, lei, period_code, counter)
    if sub and sub.state in [
        SubmissionState.VALIDATION_SUCCESSFUL,
        SubmissionState.VALIDATION_WITH_ERRORS,
        SubmissionState.VALIDATION_WITH_WARNINGS,
        SubmissionState.SUBMISSION_ACCEPTED,
    ]:
        file_data = submission_processor.get_from_storage(
            period_code, lei, str(sub.counter) + submission_processor.REPORT_QUALIFIER
        )
        return StreamingResponse(
            content=file_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{sub.counter}_validation_report.csv"',
                "Cache-Control": "no-store",
            },
        )
    else:
        raise RegTechHttpException(
            status_code=status.HTTP_404_NOT_FOUND,
            name="Report Not Found",
            detail=f"Report for ({lei}-{period_code}-{counter}) does not exist.",
        )


@router.put("/institutions/{lei}/filings/{period_code}/is-voluntary", response_model=FilingDTO)
@requires("authenticated")
async def update_is_voluntary(request: Request, lei: str, period_code: str, update_value: VoluntaryUpdateDTO):
    result = await repo.get_filing(request.state.db_session, lei, period_code)
    if result:
        result.is_voluntary = update_value.is_voluntary
        res = await repo.upsert_filing(request.state.db_session, result)
        return res
    raise RegTechHttpException(
        status_code=status.HTTP_404_NOT_FOUND,
        name="Filing Not Found",
        detail=f"A Filing for the LEI ({lei}) and period ({period_code}) that was attempted to be updated does not exist.",
    )
