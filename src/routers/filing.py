from http import HTTPStatus
from fastapi import Depends, Request, UploadFile, BackgroundTasks, status, HTTPException
from fastapi.responses import JSONResponse
from regtech_api_commons.api import Router
from services import submission_processor
from typing import Annotated, List

from entities.engine import get_session
from entities.models import FilingPeriodDTO, SubmissionDTO, FilingDTO
from entities.repos import submission_repo as repo

from sqlalchemy.ext.asyncio import AsyncSession

from starlette.authentication import requires


async def set_db(request: Request, session: Annotated[AsyncSession, Depends(get_session)]):
    request.state.db_session = session


router = Router(dependencies=[Depends(set_db)])


@router.get("/periods", response_model=List[FilingPeriodDTO])
@requires("authenticated")
async def get_filing_periods(request: Request):
    return await repo.get_filing_periods(request.state.db_session)


# This has to come after the /periods endpoint
@router.get("/{period_name}", response_model=List[FilingDTO])
async def get_filings(request: Request, period_name: str):
    try:
        return await repo.get_period_filings_for_user(request.state.db_session, period_name)
    except repo.NoFilingPeriodException as nfpe:
        raise HTTPException(status_code=500, detail=str(nfpe))


@router.post("/{lei}/submissions/{submission_id}", status_code=HTTPStatus.ACCEPTED)
async def upload_file(
    request: Request, lei: str, submission_id: str, file: UploadFile, background_tasks: BackgroundTasks
):
    content = await file.read()
    await submission_processor.upload_to_storage(lei, submission_id, content)
    background_tasks.add_task(submission_processor.validate_submission, lei, submission_id, content)


@router.get("/{lei}/filings/{filing_id}/submissions", response_model=List[SubmissionDTO])
@requires("authenticated")
async def get_submission(request: Request, lei: str, filing_id: int):
    return await repo.get_submissions(request.state.db_session, filing_id)


@router.get("/{lei}/filings/{filing_id}/submissions/latest", response_model=SubmissionDTO)
async def get_submission_latest(request: Request, lei: str, filing_id: int):
    result = await repo.get_latest_submission(request.state.db_session, filing_id)
    if result:
        return result
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
