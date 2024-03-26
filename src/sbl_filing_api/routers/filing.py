from fastapi import Depends, Request, UploadFile, BackgroundTasks, status, HTTPException
from fastapi.responses import JSONResponse
from regtech_api_commons.api.router_wrapper import Router
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
    except IntegrityError as ie:
        print(f"{ie}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Filing already exists for Filing Period {period_name} and LEI {lei}",
        )


@router.put("/institutions/{lei}/filings/{period_name}/sign", response_model=FilingDTO)
@requires("authenticated")
async def sign_filing(request: Request, lei: str, period_name: str):
    filing = await repo.get_filing(request.state.db_session, lei, period_name)
    if not filing:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=f"There is no Filing for LEI {lei} in period {period_name}, unable to sign a non-existent Filing.",
        )
    latest_sub = await repo.get_latest_submission(request.state.db_session, lei, period_name)
    if not latest_sub or latest_sub.state != SubmissionState.SUBMISSION_ACCEPTED:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=f"Cannot sign filing. Filing for {lei} for period {period_name} does not have a latest submission the SUBMISSION_ACCEPTED state.",
        )
    if not filing.contact_info:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=f"Cannot sign filing. Filing for {lei} for period {period_name} does not have contact info defined.",
        )
    sig = await repo.add_signature(
        request.state.db_session, signer_id=request.user.id, signer_name=request.user.name, filing_id=filing.id
    )
    print(f"{sig}")
    filing.confirmation_id = lei + "-" + period_name + "-" + str(latest_sub.id) + "-" + str(sig.signed_date.timestamp())
    filing.signatures.append(sig)
    return await repo.upsert_filing(request.state.db_session, filing)


@router.post("/institutions/{lei}/filings/{period_name}/submissions", response_model=SubmissionDTO)
@requires("authenticated")
async def upload_file(
    request: Request, lei: str, period_name: str, file: UploadFile, background_tasks: BackgroundTasks
):
    submission_processor.validate_file_processable(file)
    content = await file.read()

    filing = await repo.get_filing(request.state.db_session, lei, period_name)
    if not filing:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=f"There is no Filing for LEI {lei} in period {period_name}, unable to submit file.",
        )

    submission = await repo.add_submission(request.state.db_session, filing.id, request.user.id, file.filename)
    await submission_processor.upload_to_storage(period_name, lei, submission.id, content, file.filename.split(".")[-1])

    submission.state = SubmissionState.SUBMISSION_UPLOADED
    submission = await repo.update_submission(submission)
    background_tasks.add_task(submission_processor.validate_and_update_submission, lei, submission, content)

    return submission


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


@router.put("/institutions/{lei}/filings/{period_name}/submissions/{id}/accept", response_model=SubmissionDTO)
@requires("authenticated")
async def accept_submission(request: Request, id: int, lei: str, period_name: str):
    result = await repo.get_submission(request.state.db_session, id)
    if not result:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=f"Submission ID {id} does not exist, cannot accept a non-existing submission.",
        )
    if (
        result.state != SubmissionState.VALIDATION_SUCCESSFUL
        and result.state != SubmissionState.VALIDATION_WITH_WARNINGS
    ):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=f"Submission {id} for LEI {lei} in filing period {period_name} is not in an acceptable state.  Submissions must be validated successfully or with only warnings to be accepted.",
        )
    result.state = SubmissionState.SUBMISSION_ACCEPTED
    result.accepter = request.user.id
    return await repo.update_submission(result, request.state.db_session)


@router.put("/institutions/{lei}/filings/{period_name}/institution-snapshot-id", response_model=FilingDTO)
@requires("authenticated")
async def put_institution_snapshot(request: Request, lei: str, period_name: str, update_value: SnapshotUpdateDTO):
    result = await repo.get_filing(request.state.db_session, lei, period_name)
    if result:
        result.institution_snapshot_id = update_value.institution_snapshot_id
        return await repo.upsert_filing(request.state.db_session, result)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=f"A Filing for the LEI ({lei}) and period ({period_name}) that was attempted to be updated does not exist.",
    )


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


@router.put("/institutions/{lei}/filings/{period_name}/contact-info", response_model=FilingDTO)
@requires("authenticated")
async def put_contact_info(request: Request, lei: str, period_name: str, contact_info: ContactInfoDTO):
    result = await repo.get_filing(request.state.db_session, lei, period_name)
    if result:
        return await repo.update_contact_info(request.state.db_session, lei, period_name, contact_info)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=f"A Filing for the LEI ({lei}) and period ({period_name}) that was attempted to be updated does not exist.",
    )
