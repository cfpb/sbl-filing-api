import logging

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, List, TypeVar
from sbl_filing_api.entities.engine.engine import SessionLocal

from regtech_api_commons.models.auth import AuthenticatedUser

from async_lru import alru_cache

from sbl_filing_api.entities.models.dao import (
    SubmissionDAO,
    FilingPeriodDAO,
    FilingDAO,
    FilingTaskDAO,
    FilingTaskProgressDAO,
    FilingTaskState,
    ContactInfoDAO,
    UserActionDAO,
)
from sbl_filing_api.entities.models.dto import FilingPeriodDTO, FilingDTO, ContactInfoDTO, UserActionDTO
from sbl_filing_api.entities.models.model_enums import SubmissionState

logger = logging.getLogger(__name__)

T = TypeVar("T")


class NoFilingPeriodException(Exception):
    pass


async def get_submissions(session: AsyncSession, lei: str = None, filing_period: str = None) -> List[SubmissionDAO]:
    filing_id = None
    if lei and filing_period:
        filing = await get_filing(session, lei=lei, filing_period=filing_period)
        filing_id = filing.id
    return await query_helper(session, SubmissionDAO, filing=filing_id)


async def get_latest_submission(session: AsyncSession, lei: str, filing_period: str) -> SubmissionDAO | None:
    filing = await get_filing(session, lei=lei, filing_period=filing_period)
    stmt = select(SubmissionDAO).filter_by(filing=filing.id).order_by(desc(SubmissionDAO.submission_time)).limit(1)
    return await session.scalar(stmt)


async def get_filing_periods(session: AsyncSession) -> List[FilingPeriodDAO]:
    return await query_helper(session, FilingPeriodDAO)


async def get_submission(session: AsyncSession, submission_id: int) -> SubmissionDAO:
    result = await query_helper(session, SubmissionDAO, id=submission_id)
    return result[0] if result else None


async def get_submission_by_counter(session: AsyncSession, lei: str, filing_period: str, counter: int) -> SubmissionDAO:
    filing = await get_filing(session, lei=lei, filing_period=filing_period)
    result = await query_helper(session, SubmissionDAO, filing=filing.id, counter=counter)
    return result[0] if result else None


async def get_filing(session: AsyncSession, lei: str, filing_period: str) -> FilingDAO:
    result = await query_helper(session, FilingDAO, lei=lei, filing_period=filing_period)
    return result[0] if result else None


async def get_filings(session: AsyncSession, leis: list[str], filing_period: str) -> list[FilingDAO]:
    stmt = select(FilingDAO).filter(FilingDAO.lei.in_(leis), FilingDAO.filing_period == filing_period)
    result = (await session.scalars(stmt)).all()
    return result if result else []


async def get_period_filings(session: AsyncSession, filing_period: str) -> List[FilingDAO]:
    filings = await query_helper(session, FilingDAO, filing_period=filing_period)
    return filings


async def get_filing_period(session: AsyncSession, filing_period: str) -> FilingPeriodDAO:
    result = await query_helper(session, FilingPeriodDAO, code=filing_period)
    return result[0] if result else None


@alru_cache(maxsize=128)
async def get_filing_tasks(session: AsyncSession) -> List[FilingTaskDAO]:
    return await query_helper(session, FilingTaskDAO)


async def get_user_action(session: AsyncSession, id: int) -> UserActionDAO:
    result = await query_helper(session, UserActionDAO, id=id)
    return result[0] if result else None


async def get_user_actions(session: AsyncSession) -> List[UserActionDAO]:
    return await query_helper(session, UserActionDAO)


async def add_submission(session: AsyncSession, filing_id: int, filename: str, submitter_id: int) -> SubmissionDAO:
    stmt = select(SubmissionDAO).filter_by(filing=filing_id).order_by(desc(SubmissionDAO.counter)).limit(1)
    last_sub = await session.scalar(stmt)
    current_count = last_sub.counter if last_sub else 0
    new_sub = SubmissionDAO(
        filing=filing_id,
        state=SubmissionState.SUBMISSION_STARTED,
        filename=filename,
        submitter_id=submitter_id,
        counter=(current_count + 1),
    )
    # this returns the attached object, most importantly with the new submission id
    new_sub = await session.merge(new_sub)
    await session.commit()
    return new_sub


async def update_submission(session: AsyncSession, submission: SubmissionDAO) -> SubmissionDAO:
    return await upsert_helper(session, submission, SubmissionDAO)


async def expire_submission(submission_id: int):
    async with SessionLocal() as session:
        submission = await get_submission(session, submission_id)
        submission.state = SubmissionState.VALIDATION_EXPIRED
        await upsert_helper(session, submission, SubmissionDAO)


async def error_out_submission(submission_id: int):
    async with SessionLocal() as session:
        submission = await get_submission(session, submission_id)
        submission.state = SubmissionState.VALIDATION_ERROR
        await upsert_helper(session, submission, SubmissionDAO)


async def upsert_filing_period(session: AsyncSession, filing_period: FilingPeriodDTO) -> FilingPeriodDAO:
    return await upsert_helper(session, filing_period, FilingPeriodDAO)


async def upsert_filing(session: AsyncSession, filing: FilingDTO) -> FilingDAO:
    return await upsert_helper(session, filing, FilingDAO)


async def create_new_filing(session: AsyncSession, lei: str, filing_period: str, creator_id: int) -> FilingDAO:
    new_filing = FilingDAO(filing_period=filing_period, lei=lei, creator_id=creator_id)
    return await upsert_helper(session, new_filing, FilingDAO)


async def update_task_state(
    session: AsyncSession, lei: str, filing_period: str, task_name: str, state: FilingTaskState, user: AuthenticatedUser
):
    filing = await get_filing(session, lei=lei, filing_period=filing_period)
    found_task = await query_helper(session, FilingTaskProgressDAO, filing=filing.id, task_name=task_name)
    if found_task:
        task = found_task[0]  # should only be one
        task.state = state
        task.user = user.username
    else:
        task = FilingTaskProgressDAO(filing=filing.id, state=state, task_name=task_name, user=user.username)
    await upsert_helper(session, task, FilingTaskProgressDAO)


async def update_contact_info(
    session: AsyncSession, lei: str, filing_period: str, new_contact_info: ContactInfoDTO
) -> FilingDAO:
    filing = await get_filing(session, lei=lei, filing_period=filing_period)
    if filing.contact_info:
        for key, value in new_contact_info.__dict__.items():
            if key != "id":
                setattr(filing.contact_info, key, value)
    else:
        filing.contact_info = ContactInfoDAO(**new_contact_info.__dict__.copy(), filing=filing.id)
    return await upsert_helper(session, filing, FilingDAO)


async def add_user_action(
    session: AsyncSession,
    new_user_action: UserActionDTO,
) -> UserActionDAO:
    return await upsert_helper(session, new_user_action, UserActionDAO)


async def upsert_helper(session: AsyncSession, original_data: Any, table_obj: T) -> T:
    copy_data = original_data.__dict__.copy()
    # this is only for if a DAO is passed in
    # Should be DTOs, but hey, it's python
    if "_sa_instance_state" in copy_data:
        del copy_data["_sa_instance_state"]
    new_dao = table_obj(**copy_data)
    new_dao = await session.merge(new_dao)
    await session.commit()
    await session.refresh(new_dao)
    return new_dao


async def query_helper(session: AsyncSession, table_obj: T, **filter_args) -> List[T]:
    stmt = select(table_obj)
    # remove empty args
    filter_args = {k: v for k, v in filter_args.items() if v is not None}
    if filter_args:
        stmt = stmt.filter_by(**filter_args)
    return (await session.scalars(stmt)).all()
