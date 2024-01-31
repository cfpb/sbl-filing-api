from http import HTTPStatus
from fastapi import Depends, Request, UploadFile, BackgroundTasks
from regtech_api_commons.api import Router
from services import submission_processor
from typing import Annotated, List

from entities.engine import get_session
from entities.models import FilingPeriodDTO, SubmissionDTO
from entities.repos import submission_repo as repo

from sqlalchemy.ext.asyncio import AsyncSession


async def set_db(request: Request, session: Annotated[AsyncSession, Depends(get_session)]):
    request.state.db_session = session


router = Router(dependencies=[Depends(set_db)])


@router.get("/periods", response_model=List[FilingPeriodDTO])
async def get_filing_periods(request: Request):
    return await repo.get_filing_periods(request.state.db_session)


@router.post("/{lei}/submissions/{submission_id}", status_code=HTTPStatus.ACCEPTED)
async def upload_file(
    request: Request, lei: str, submission_id: str, file: UploadFile, background_tasks: BackgroundTasks
):
    content = await file.read()
    await submission_processor.upload_to_storage(lei, submission_id, content)
    background_tasks.add_task(submission_processor.validate_submission, lei, submission_id, content)


@router.get("/{lei}/filings/{filing_id}/submissions", response_model=List[SubmissionDTO])
async def get_submission(request: Request, lei: str, filing_id: int):
    return await repo.get_submissions(request.state.db_session, filing_id)
