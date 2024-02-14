from http import HTTPStatus
from fastapi import Depends, Request, UploadFile, BackgroundTasks, status
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
@router.get("/{lei}/{period_name}", response_model=FilingDTO)
async def get_filing(request: Request, lei: str, period_name: str):
    return await repo.get_filing(request.state.db_session, lei, period_name)


@router.post("/{lei}/{period_name}", response_model=FilingDTO)
async def post_filing(request: Request, lei: str, period_name: str, filing_obj: FilingDTO = None):
    if filing_obj:
        return await repo.upsert_filing(request.state.db_session, filing_obj)
    else:
        return await repo.create_new_filing(request.state.db_session, lei, period_name)


@router.post("/{lei}/submissions/{submission_id}", status_code=HTTPStatus.ACCEPTED)
async def upload_file(
    request: Request, lei: str, submission_id: str, file: UploadFile, background_tasks: BackgroundTasks
):
    content = await file.read()
    await submission_processor.upload_to_storage(lei, submission_id, content)
    background_tasks.add_task(submission_processor.validate_submission, lei, submission_id, content)


@router.get("/{lei}/{period_name}/submissions", response_model=List[SubmissionDTO])
@requires("authenticated")
async def get_submission(request: Request, lei: str, period_name: str):
    return await repo.get_submissions(request.state.db_session, lei, period_name)


@router.get("/{lei}/{period_name}/submissions/latest", response_model=SubmissionDTO)
async def get_submission_latest(request: Request, lei: str, period_name: str):
    result = await repo.get_latest_submission(request.state.db_session, lei, period_name)
    if result:
        return result
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)