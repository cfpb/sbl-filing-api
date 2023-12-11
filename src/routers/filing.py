from http import HTTPStatus
from fastapi import Request, UploadFile, BackgroundTasks
from regtech_api_commons.api import Router
from services import submission_processor

router = Router()


@router.post("/{lei}/submissions/{submission_id}", status_code=HTTPStatus.ACCEPTED)
async def upload_file(
    request: Request, lei: str, submission_id: str, file: UploadFile, background_tasks: BackgroundTasks
):
    content = await file.read()
    await submission_processor.upload_to_storage(lei, submission_id, content)
    background_tasks.add_task(submission_processor.validate_submission, lei, submission_id, content)
