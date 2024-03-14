from datetime import datetime
from http import HTTPStatus
from fastapi import Depends, Request, UploadFile, BackgroundTasks, status, HTTPException
from fastapi.responses import JSONResponse
from regtech_api_commons.api import Router
from services import submission_processor
from typing import Annotated, List

from entities.engine import get_session
from entities.models import (
    FilingPeriodDTO,
    SubmissionDTO,
    FilingDTO,
    SnapshotUpdateDTO,
    StateUpdateDTO,
    ContactInfoDTO,
    SubmissionState,
    SignatureDAO,
)
from entities.repos import submission_repo as repo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from starlette.authentication import requires

from .dependencies import verify_user_lei_relation


async def set_db(request: Request, session: Annotated[AsyncSession, Depends(get_session)]):
    request.state.db_session = session


router = Router(dependencies=[Depends(set_db), Depends(verify_user_lei_relation)])


@router.get("/periods", response_model=List[FilingPeriodDTO])
@requires("authenticated")
async def get_filing_periods(request: Request):
    return await repo.get_filing_periods(request.state.db_session)


@router.get("/institutions/{lei}/filings/{period_name}", response_model=FilingDTO)
@requires("authenticated")
async def get_filing(request: Request, lei: str, period_name: str):
    res = await repo.get_filing(request.state.db_session, lei, period_name)
    if not res:
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
    return res


@router.post("/institutions/{lei}/filings/{period_name}", response_model=FilingDTO)
@requires("authenticated")
async def post_filing(request: Request, lei: str, period_name: str):
    try:
        return await repo.create_new_filing(request.state.db_session, lei, period_name)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Filing already exists for Filing Period {period_name} and LEI {lei}",
        )


@router.put("/institutions/{lei}/filings/{period_name}/sign", response_model=FilingDTO)
@requires("authenticated")
async def sign_filing(request: Request, lei: str, period_name: str):
    res = await repo.get_filing(request.state.db_session, lei, period_name)
    if not res:
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
    latest_sub = await repo.get_latest_submission(request.state.db_session, lei, period_name)
    if not latest_sub or latest_sub.state != SubmissionState.SUBMISSION_CERTIFIED:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=f"Cannot sign filing.  Filing for {lei} for period {period_name} does not have a latest submission the SUBMISSION_CERTIFIED state.")
    if not res.contact_info:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=f"Cannot sign filing. Filing for {lei} for period {period_name} does not have contact info defined.")
    res.signer = SignatureDAO(signer=request.user.id, filing=res.id)
    res.confirmation_id = (lei+"-"+period_name+"-"+latest_sub.id+"-"+datetime.now().timestamp())
    return await repo.upsert_filing(request.state.db_session, res)


@router.post("/{lei}/submissions/{submission_id}", status_code=HTTPStatus.ACCEPTED)
@requires("authenticated")
async def upload_file(
    request: Request, lei: str, submission_id: str, file: UploadFile, background_tasks: BackgroundTasks
):
    submission_processor.validate_file_processable(file)
    content = await file.read()
    await submission_processor.upload_to_storage(lei, submission_id, content, file.filename.split(".")[-1])
    background_tasks.add_task(submission_processor.validate_submission, lei, submission_id, content, background_tasks)


@router.get("/institutions/{lei}/filings/{period_name}/submissions", response_model=List[SubmissionDTO])
@requires("authenticated")
async def get_submissions(request: Request, lei: str, period_name: str):
    return await repo.get_submissions(request.state.db_session, lei, period_name)


@router.get("/institutions/{lei}/filings/{period_name}/submissions/latest", response_model=SubmissionDTO)
@requires("authenticated")
async def get_submission_latest(request: Request, lei: str, period_name: str):
    result = await repo.get_latest_submission(request.state.db_session, lei, period_name)
    if result:
        return result
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)


@router.get("/institutions/{lei}/filings/{period_name}/submissions/{id}", response_model=SubmissionDTO)
@requires("authenticated")
async def get_submission(request: Request, id: int):
    result = await repo.get_submission(request.state.db_session, id)
    if result:
        return result
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)


@router.put("/institutions/{lei}/filings/{period_name}/submissions/{id}/certify", response_model=SubmissionDTO)
@requires("authenticated")
async def certify_submission(request: Request, id: int, lei: str, period_name: str):
    result = await repo.get_submission(request.state.db_session, id)
    if not result:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=f"Submission ID {id} does not exist, cannot certify a non-existing submission.",
        )
    if (
        result.state != SubmissionState.VALIDATION_SUCCESSFUL
        and result.state != SubmissionState.VALIDATION_WITH_WARNINGS
    ):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=f"Submission {id} for LEI {lei} in filing period {period_name} is not in a certifiable state.  Submissions must be validated successfully or with only warnings to be signed",
        )
    result.state = SubmissionState.SUBMISSION_CERTIFIED
    return await repo.update_submission(result, request.state.db_session)


@router.put("/institutions/{lei}/filings/{period_name}/institution-snapshot-id", response_model=FilingDTO)
@requires("authenticated")
async def put_institution_snapshot(request: Request, lei: str, period_name: str, update_value: SnapshotUpdateDTO):
    result = await repo.get_filing(request.state.db_session, lei, period_name)
    if result:
        result.institution_snapshot_id = update_value.institution_snapshot_id
        return await repo.upsert_filing(request.state.db_session, result)
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)


@router.post("/institutions/{lei}/filings/{period_name}/tasks/{task_name}")
@requires("authenticated")
async def update_task_state(request: Request, lei: str, period_name: str, task_name: str, state: StateUpdateDTO):
    await repo.update_task_state(request.state.db_session, lei, period_name, task_name, state.state, request.user)


@router.get("/institutions/{lei}/filings/{period_name}/contact-info", response_model=ContactInfoDTO)
@requires("authenticated")
async def get_contact_info(request: Request, lei: str, period_name: str):
    result = await repo.get_contact_info(request.state.db_session, lei, period_name)
    if result:
        return result
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)


@router.put("/institutions/{lei}/filings/{period_name}/contact-info", response_model=ContactInfoDTO)
@requires("authenticated")
async def put_contact_info(request: Request, lei: str, period_name: str, contact_info: ContactInfoDTO):
    return await repo.update_contact_info(request.state.db_session, lei, period_name, contact_info)
