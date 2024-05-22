import asyncio
import logging

from sbl_filing_api.config import settings
from sbl_filing_api.entities.models.dao import SubmissionDAO
from sbl_filing_api.entities.repos import submission_repo as repo
from sbl_filing_api.services.submission_processor import validate_and_update_submission


logger = logging.getLogger(__name__)


def handle_submission(period_code: str, lei: str, submission: SubmissionDAO, content: bytes, exec_check):
    loop = asyncio.get_event_loop()
    try:
        coro = validate_and_update_submission(period_code, lei, submission, content, exec_check)
        loop.run_until_complete(coro)
    except Exception as e:
        logger.error(e, exc_info=True, stack_info=True)


async def check_future(future, submission_id, exec_check):
    await asyncio.sleep(settings.expired_submission_check_secs)
    try:
        future.result()
    except asyncio.InvalidStateError:
        future.cancel()
        exec_check["continue"] = False
        await repo.expire_submission(submission_id)
        logger.warning(
            f"Validation for submission {submission_id} did not complete within the expected timeframe, will be set to VALIDATION_EXPIRED."
        )
    except Exception:
        exec_check["continue"] = False
        await repo.error_out_submission(submission_id)
        logger.error(
            f"Validation for submission {submission_id} did not complete due to an unexpected error.",
            exc_info=True,
            stack_info=True,
        )
