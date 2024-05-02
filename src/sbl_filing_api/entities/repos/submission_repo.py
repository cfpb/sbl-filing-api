import logging

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, List, TypeVar
from sbl_filing_api.entities.engine.engine import SessionLocal

from regtech_api_commons.models.auth import AuthenticatedUser

from copy import deepcopy

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
from sbl_filing_api.entities.models.dto import FilingPeriodDTO, FilingDTO, ContactInfoDTO
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


async def get_filing(session: AsyncSession, lei: str, filing_period: str) -> FilingDAO:
    result = await query_helper(session, FilingDAO, lei=lei, filing_period=filing_period)
    if result:
        result = await populate_missing_tasks(session, result)
    return result[0] if result else None


async def get_period_filings(session: AsyncSession, filing_period: str) -> List[FilingDAO]:
    filings = await query_helper(session, FilingDAO, filing_period=filing_period)
    if filings:
        filings = await populate_missing_tasks(session, filings)
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
    new_sub = SubmissionDAO(
        filing=filing_id, state=SubmissionState.SUBMISSION_STARTED, filename=filename, submitter_id=submitter_id
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


async def upsert_filing_period(session: AsyncSession, filing_period: FilingPeriodDTO) -> FilingPeriodDAO:
    return await upsert_helper(session, filing_period, FilingPeriodDAO)


async def upsert_filing(session: AsyncSession, filing: FilingDTO) -> FilingDAO:
    return await upsert_helper(session, filing, FilingDAO)


async def create_new_filing(session: AsyncSession, lei: str, filing_period: str, creator_id: int) -> FilingDAO:
    new_filing = FilingDAO(filing_period=filing_period, lei=lei, creator_id=creator_id)
    new_filing = await upsert_helper(session, new_filing, FilingDAO)
    new_filing = await populate_missing_tasks(session, [new_filing])
    return new_filing[0]


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
    filing.contact_info = ContactInfoDAO(**new_contact_info.__dict__.copy(), filing=filing.id)
    return await upsert_helper(session, filing, FilingDAO)


async def add_user_action(
    session: AsyncSession,
    user_id: int,
    user_name: str,
    user_email: str,
    action_type: str,
) -> UserActionDAO:
    new_user_Action = UserActionDAO(
        user_id=user_id,
        user_name=user_name,
        user_email=user_email,
        action_type=action_type,
    )
    return await upsert_helper(session, new_user_Action, UserActionDAO)


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


async def populate_missing_tasks(session: AsyncSession, filings: List[FilingDAO]):
    filing_tasks = await get_filing_tasks(session)
    filings_copy = deepcopy(filings)
    for f in filings_copy:
        tasks = [t.task.name for t in f.tasks]
        missing_tasks = [t for t in filing_tasks if t.name not in tasks]
        for mt in missing_tasks:
            f.tasks.append(
                FilingTaskProgressDAO(
                    filing=f.id,
                    task_name=mt.name,
                    task=mt,
                    state=FilingTaskState.NOT_STARTED,
                    user="",
                )
            )

    return filings_copy
