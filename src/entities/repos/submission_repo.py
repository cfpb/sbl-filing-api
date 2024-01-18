from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, List, TypeVar

from entities.models import (
    SubmissionDAO,
    SubmissionDTO,
    SubmissionState,
    FilingPeriodDAO,
    FilingPeriodDTO,
    FilingDTO,
    FilingDAO,
)

T = TypeVar("T")


async def get_submissions(session: AsyncSession, filing_id: int = None) -> List[SubmissionDAO]:
    async with session.begin():
        stmt = select(SubmissionDAO)
        if filing_id:
            stmt = stmt.filter(SubmissionDAO.filing == filing_id)
        results = await session.scalars(stmt)
        return results.all()


async def get_submission(session: AsyncSession, submission_id: int) -> SubmissionDAO:
    return await query_helper(session, submission_id, SubmissionDAO)


async def get_filing(session: AsyncSession, filing_id: int) -> FilingDAO:
    return await query_helper(session, filing_id, FilingDAO)


async def get_filing_period(session: AsyncSession, filing_period_id: int) -> FilingPeriodDAO:
    return await query_helper(session, filing_period_id, FilingPeriodDAO)


async def add_submission(session: AsyncSession, submission: SubmissionDTO) -> SubmissionDAO:
    async with session.begin():
        new_sub = SubmissionDAO(
            filing=submission.filing,
            submitter=submission.submitter,
            state=SubmissionState.SUBMISSION_UPLOADED,
            validation_ruleset_version="v1",
        )
        # this returns the attached object, most importantly with the new submission id
        new_sub = await session.merge(new_sub)
        await session.commit()
        return new_sub


async def upsert_filing_period(session: AsyncSession, filing_period: FilingPeriodDTO) -> FilingPeriodDAO:
    return await upsert_helper(session, filing_period, FilingPeriodDAO)


async def upsert_filing(session: AsyncSession, filing: FilingDTO) -> FilingDAO:
    return await upsert_helper(session, filing, FilingDAO)


async def upsert_helper(session: AsyncSession, original_data: Any, type: T) -> T:
    async with session.begin():
        copy_data = original_data.__dict__.copy()
        # this is only for if a DAO is passed in
        # Should be DTOs, but hey, it's python
        if copy_data["id"] is not None and "_sa_instance_state" in copy_data:
            del copy_data["_sa_instance_state"]
        new_dao = type(**copy_data)
        new_dao = await session.merge(new_dao)
        await session.commit()
        return new_dao


async def query_helper(session: AsyncSession, id: int, type: T) -> T:
    async with session.begin():
        stmt = select(type).filter(type.id == id)
        return await session.scalar(stmt)
