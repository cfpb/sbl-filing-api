from fastapi import Depends, Request, UploadFile, BackgroundTasks, status
from fastapi.responses import Response, JSONResponse, FileResponse
from regtech_api_commons.api.router_wrapper import Router
from regtech_api_commons.api.exceptions import RegTechHttpException
from sbl_filing_api.entities.models.model_enums import UserActionType
from sbl_filing_api.services import submission_processor
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
)

from sbl_filing_api.entities.repos import submission_repo as repo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from starlette.authentication import requires

from sbl_filing_api.routers.dependencies import verify_user_lei_relation


async def set_db(request: Request, session: Annotated[AsyncSession, Depends(get_session)]):
    request.state.db_session = session


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
    response.status_code = status.HTTP_404_NOT_FOUND


@router.post("/institutions/{lei}/filings/{period_code}", response_model=FilingDTO)
@requires("authenticated")
async def post_filing(request: Request, lei: str, period_code: str):
    period = await repo.get_filing_period(request.state.db_session, filing_period=period_code)

    if period:
        creator = None
        try:
            creator = await repo.add_user_action(
                request.state.db_session,
                user_id=request.user.id,
                user_name=request.user.name,
                user_email=request.user.email,
                action_type=UserActionType.CREATE,
            )
        except Exception as e:
            # logger.error("Error while trying to process CREATE User Action", e)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=f"{e}",
            )

        try:
            return await repo.create_new_filing(request.state.db_session, lei, period_code, creator_id=creator.id)
        except IntegrityError:
            raise RegTechHttpException(
                status_code=status.HTTP_409_CONFLICT,
                name="Filing Creation Conflict",
                detail=f"Filing already exists for Filing Period {period_code} and LEI {lei}",
            )

    else:
        raise RegTechHttpException(
            status_code=status.HTTP_404_NOT_FOUND,
            name="Filing Period Not Found",
            detail=f"The period ({period_code}) does not exist, therefore a Filing can not be created for this period.",
        )


@router.put("/institutions/{lei}/filings/{period_code}/sign", response_model=FilingDTO)
@requires("authenticated")
async def sign_filing(request: Request, lei: str, period_code: str):
    filing = await repo.get_filing(request.state.db_session, lei, period_code)
    if not filing:
        raise RegTechHttpException(
            status_code=status.HTTP_404_NOT_FOUND,
            name="Filing Not Found",
            detail=f"There is no Filing for LEI {lei} in period {period_code}, unable to sign a non-existent Filing.",
        )
    latest_sub = await repo.get_latest_submission(request.state.db_session, lei, period_code)
    if not latest_sub or latest_sub.state != SubmissionState.SUBMISSION_ACCEPTED:
        raise RegTechHttpException(
            status_code=status.HTTP_403_FORBIDDEN,
            name="Filing Action Forbidden",
            detail=f"Cannot sign filing. Filing for {lei} for period {period_code} does not have a latest submission the SUBMISSION_ACCEPTED state.",
        )
    if not filing.contact_info:
        raise RegTechHttpException(
            status_code=status.HTTP_403_FORBIDDEN,
            name="Filing Action Forbidden",
            detail=f"Cannot sign filing. Filing for {lei} for period {period_code} does not have contact info defined.",
        )
    """
    if not filing.institution_snapshot_id:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=f"Cannot sign filing. Filing for {lei} for period {period_code} does not have institution snapshot id defined.",
        )
    """

    sig = await repo.add_user_action(
        request.state.db_session,
        user_id=request.user.id,
        user_name=request.user.name,
        user_email=request.user.email,
        action_type=UserActionType.SIGN,
    )
    filing.confirmation_id = lei + "-" + period_code + "-" + str(latest_sub.id) + "-" + str(sig.timestamp.timestamp())
    filing.signatures.append(sig)
    return await repo.upsert_filing(request.state.db_session, filing)


@router.post("/institutions/{lei}/filings/{period_code}/submissions", response_model=SubmissionDTO)
@requires("authenticated")
async def upload_file(
    request: Request, lei: str, period_code: str, file: UploadFile, background_tasks: BackgroundTasks
):
    submission_processor.validate_file_processable(file)
    content = await file.read()

    filing = await repo.get_filing(request.state.db_session, lei, period_code)
    if not filing:
        raise RegTechHttpException(
            status_code=status.HTTP_404_NOT_FOUND,
            name="Filing Not Found",
            detail=f"There is no Filing for LEI {lei} in period {period_code}, unable to submit file.",
        )
    try:
        submitter = await repo.add_user_action(
            request.state.db_session,
            user_id=request.user.id,
            user_name=request.user.name,
            user_email=request.user.email,
            action_type=UserActionType.SUBMIT,
        )
        submission = await repo.add_submission(request.state.db_session, filing.id, file.filename, submitter.id)
        try:
            await submission_processor.upload_to_storage(
                period_code, lei, submission.id, content, file.filename.split(".")[-1]
            )

            submission.state = SubmissionState.SUBMISSION_UPLOADED
            submission = await repo.update_submission(submission)
        except Exception as e:
            submission.state = SubmissionState.UPLOAD_FAILED
            submission = await repo.update_submission(submission)
            raise RegTechHttpException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                name="Submission Unprocessable",
                detail=f"Error while trying to process Submission {submission.id}",
            ) from e
        background_tasks.add_task(submission_processor.validation_monitor, period_code, lei, submission, content)

        return submission

    except Exception as e:
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
    result = await repo.get_latest_submission(request.state.db_session, lei, period_code)
    if result:
        return result
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/institutions/{lei}/filings/{period_code}/submissions/{id}", response_model=SubmissionDTO | None)
@requires("authenticated")
async def get_submission(request: Request, response: Response, id: int):
    result = await repo.get_submission(request.state.db_session, id)
    if result:
        return result
    response.status_code = status.HTTP_404_NOT_FOUND


@router.put("/institutions/{lei}/filings/{period_code}/submissions/{id}/accept", response_model=SubmissionDTO)
@requires("authenticated")
async def accept_submission(request: Request, id: int, lei: str, period_code: str):
    submission = await repo.get_submission(request.state.db_session, id)
    if not submission:
        raise RegTechHttpException(
            status_code=status.HTTP_404_NOT_FOUND,
            name="Submission Not Found",
            detail=f"Submission ID {id} does not exist, cannot accept a non-existing submission.",
        )
    if (
        submission.state != SubmissionState.VALIDATION_SUCCESSFUL
        and submission.state != SubmissionState.VALIDATION_WITH_WARNINGS
    ):
        raise RegTechHttpException(
            status_code=status.HTTP_403_FORBIDDEN,
            name="Submission Action Forbidden",
            detail=f"Submission {id} for LEI {lei} in filing period {period_code} is not in an acceptable state.  Submissions must be validated successfully or with only warnings to be accepted.",
        )

    accepter = await repo.add_user_action(
        request.state.db_session,
        user_id=request.user.id,
        user_name=request.user.name,
        user_email=request.user.email,
        action_type=UserActionType.ACCEPT,
    )

    submission.accepter_id = accepter.id
    submission.state = SubmissionState.SUBMISSION_ACCEPTED
    submission = await repo.update_submission(submission, request.state.db_session)
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
    latest_sub = await repo.get_latest_submission(request.state.db_session, lei, period_code)
    if latest_sub:
        file_data = await submission_processor.get_from_storage(
            period_code, lei, str(latest_sub.id) + submission_processor.REPORT_QUALIFIER
        )
        return FileResponse(path=file_data, media_type="text/csv", filename=f"{latest_sub.id}_validation_report.csv")
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)


@router.get(
    "/institutions/{lei}/filings/{period_code}/submissions/{id}/report",
    responses={200: {"content": {"text/plain; charset=utf-8": {}}}},
)
@requires("authenticated")
async def get_submission_report(request: Request, response: Response, lei: str, period_code: str, id: int):
    sub = await repo.get_submission(request.state.db_session, id)
    if sub:
        file_data = await submission_processor.get_from_storage(
            period_code, lei, str(sub.id) + submission_processor.REPORT_QUALIFIER
        )
        return FileResponse(path=file_data, media_type="text/csv", filename=f"{sub.id}_validation_report.csv")
    response.status_code = status.HTTP_404_NOT_FOUND
