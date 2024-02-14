import logging

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, List, TypeVar
from entities.engine import get_session
from regtech_api_commons.models.auth import AuthenticatedUser

from copy import deepcopy

from async_lru import alru_cache

from entities.models import (
    SubmissionDAO,
    SubmissionDTO,
    SubmissionState,
    FilingPeriodDAO,
    FilingPeriodDTO,
    FilingDTO,
    FilingDAO,
    FilingTaskDAO,
    FilingTaskStateDAO,
    FilingTaskState,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class NoFilingPeriodException(Exception):
    pass


async def get_submissions(session: AsyncSession, filing_id: int = None) -> List[SubmissionDAO]:
    return await query_helper(session, SubmissionDAO, "filing", filing_id)


async def get_latest_submission(session: AsyncSession, filing_id: int) -> List[SubmissionDAO]:
    async with session.begin():
        stmt = (
            select(SubmissionDAO)
            .filter(SubmissionDAO.filing == filing_id)
            .order_by(desc(SubmissionDAO.submission_time))
            .limit(1)
        )
        return await session.scalar(stmt)


async def get_filing_periods(session: AsyncSession) -> List[FilingPeriodDAO]:
    return await query_helper(session, FilingPeriodDAO)


async def get_submission(session: AsyncSession, submission_id: int) -> SubmissionDAO:
    result = await query_helper(session, SubmissionDAO, "id", submission_id)
    return result[0] if result else None


async def get_filing(session: AsyncSession, filing_id: int) -> FilingDAO:
    result = await query_helper(session, FilingDAO, "id", filing_id)
    if result:
        result = await populate_missing_tasks(session, result)
    return result[0] if result else None


async def get_period_filings_for_user(
    session: AsyncSession, user: AuthenticatedUser, period_name: str
) -> List[FilingDAO]:
    filing_period = await query_helper(session, FilingPeriodDAO, "name", period_name)
    if filing_period:
        filings = await query_helper(session, FilingDAO, "filing_period", filing_period[0].id)
        filings = [f for f in filings if f.lei in user.institutions]
        if filings:
            filings = await populate_missing_tasks(session, filings)

        return filings
    else:
        raise NoFilingPeriodException(f"There is no Filing Period with name {period_name} defined in the database.")


async def get_filing_period(session: AsyncSession, filing_period_id: int) -> FilingPeriodDAO:
    result = await query_helper(session, FilingPeriodDAO, "id", filing_period_id)
    return result[0] if result else None


@alru_cache(maxsize=128)
async def get_filing_tasks(session: AsyncSession) -> List[FilingTaskDAO]:
    return await query_helper(session, FilingTaskDAO)


async def add_submission(session: AsyncSession, submission: SubmissionDTO) -> SubmissionDAO:
    async with session.begin():
        new_sub = SubmissionDAO(
            filing=submission.filing,
            submitter=submission.submitter,
            state=SubmissionState.SUBMISSION_UPLOADED,
        )
        # this returns the attached object, most importantly with the new submission id
        new_sub = await session.merge(new_sub)
        await session.commit()
        return new_sub


async def update_submission(submission: SubmissionDAO, incoming_session: AsyncSession = None) -> SubmissionDAO:
    session = incoming_session if incoming_session else await anext(get_session())
    async with session.begin():
        try:
            new_sub = await session.merge(submission)
            await session.commit()
            return new_sub
        except Exception as e:
            await session.rollback()
            logger.error(f"There was an exception storing the updated SubmissionDAO, rolling back transaction: {e}")
            raise


async def upsert_filing_period(session: AsyncSession, filing_period: FilingPeriodDTO) -> FilingPeriodDAO:
    return await upsert_helper(session, filing_period, FilingPeriodDAO)


async def upsert_filing(session: AsyncSession, filing: FilingDTO) -> FilingDAO:
    return await upsert_helper(session, filing, FilingDAO)


async def upsert_helper(session: AsyncSession, original_data: Any, table_obj: T) -> T:
    copy_data = original_data.__dict__.copy()
    # this is only for if a DAO is passed in
    # Should be DTOs, but hey, it's python
    if copy_data["id"] is not None and "_sa_instance_state" in copy_data:
        del copy_data["_sa_instance_state"]
    new_dao = table_obj(**copy_data)
    new_dao = await session.merge(new_dao)
    await session.commit()
    return new_dao


async def query_helper(session: AsyncSession, table_obj: T, column_name: str = None, value: Any = None) -> List[T]:
    stmt = select(table_obj)
    if column_name and value:
        stmt = stmt.filter(getattr(table_obj, column_name) == value)
    return (await session.scalars(stmt)).all()


async def populate_missing_tasks(session: AsyncSession, filings: List[FilingDAO]) -> List[FilingDAO]:
    filing_tasks = await get_filing_tasks(session)
    filings_copy = deepcopy(filings)
    for f in filings_copy:
        tasks = [t.task for t in f.tasks]
        missing_tasks = [t for t in filing_tasks if t not in tasks]
        for mt in missing_tasks:
            f.tasks.append(
                FilingTaskStateDAO(filing=f.id, task_name=mt.name, state=FilingTaskState.NOT_STARTED, user="")
            )
    return filings_copy
