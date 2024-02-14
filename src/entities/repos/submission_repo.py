import logging

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, List, TypeVar
from entities.engine import get_session

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


async def get_submissions(session: AsyncSession, lei: str = None, filing_period: str = None) -> List[SubmissionDAO]:
    return await query_helper(session, SubmissionDAO, lei=lei, filing_period=filing_period)


async def get_latest_submission(session: AsyncSession, lei: str, filing_period: str) -> List[SubmissionDAO]:
    async with session.begin():
        stmt = (
            select(SubmissionDAO)
            .filter_by(lei=lei, filing_period=filing_period)
            .order_by(desc(SubmissionDAO.submission_time))
            .limit(1)
        )
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


async def get_period_filings(session: AsyncSession, lei: str, filing_period: str) -> List[FilingDAO]:
    filings = await query_helper(session, FilingDAO, lei=lei, filing_period=filing_period)
    if filings:
        filings = await populate_missing_tasks(session, filings)

    return filings


async def get_filing_period(session: AsyncSession, filing_period: str) -> FilingPeriodDAO:
    result = await query_helper(session, FilingPeriodDAO, name=filing_period)
    return result[0] if result else None


@alru_cache(maxsize=128)
async def get_filing_tasks(session: AsyncSession) -> List[FilingTaskDAO]:
    return await query_helper(session, FilingTaskDAO)


async def add_submission(session: AsyncSession, submission: SubmissionDTO) -> SubmissionDAO:
    async with session.begin():
        new_sub = SubmissionDAO(
            filing_period=submission.filing_period,
            lei=submission.lei,
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
    if "_sa_instance_state" in copy_data:
        del copy_data["_sa_instance_state"]
    new_dao = table_obj(**copy_data)
    new_dao = await session.merge(new_dao)
    await session.commit()
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
        tasks = [t.task for t in f.tasks]
        missing_tasks = [t for t in filing_tasks if t not in tasks]
        for mt in missing_tasks:
            f.tasks.append(
                FilingTaskStateDAO(
                    filing_period=f.filing_period,
                    lei=f.lei,
                    task_name=mt.name,
                    state=FilingTaskState.NOT_STARTED,
                    user="",
                )
            )

    return filings_copy
