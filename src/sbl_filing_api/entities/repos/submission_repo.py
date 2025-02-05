import logging

from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from typing import Any, List, TypeVar
from sbl_filing_api.entities.engine.engine import SessionLocal

from regtech_api_commons.models.auth import AuthenticatedUser

from functools import lru_cache

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


def get_submissions(session: Session, lei: str = None, filing_period: str = None) -> List[SubmissionDAO]:
    filing_id = None
    if lei and filing_period:
        filing = get_filing(session, lei=lei, filing_period=filing_period)
        filing_id = filing.id
    return query_helper(session, SubmissionDAO, filing=filing_id)


def get_latest_submission(session: Session, lei: str, filing_period: str) -> SubmissionDAO | None:
    filing = get_filing(session, lei=lei, filing_period=filing_period)
    stmt = select(SubmissionDAO).filter_by(filing=filing.id).order_by(desc(SubmissionDAO.submission_time)).limit(1)
    return session.scalar(stmt)


def get_filing_periods(session: Session) -> List[FilingPeriodDAO]:
    return query_helper(session, FilingPeriodDAO)


def get_submission(session: Session, submission_id: int) -> SubmissionDAO:
    result = query_helper(session, SubmissionDAO, id=submission_id)
    return result[0] if result else None


def get_submission_by_counter(session: Session, lei: str, filing_period: str, counter: int) -> SubmissionDAO:
    filing = get_filing(session, lei=lei, filing_period=filing_period)
    result = query_helper(session, SubmissionDAO, filing=filing.id, counter=counter)
    return result[0] if result else None


def get_filing(session: Session, lei: str, filing_period: str) -> FilingDAO:
    result = query_helper(session, FilingDAO, lei=lei, filing_period=filing_period)
    return result[0] if result else None


def get_filings(session: Session, leis: list[str], filing_period: str) -> list[FilingDAO]:
    stmt = select(FilingDAO).filter(FilingDAO.lei.in_(leis), FilingDAO.filing_period == filing_period)
    result = (session.scalars(stmt)).all()
    return result if result else []


def get_period_filings(session: Session, filing_period: str) -> List[FilingDAO]:
    filings = query_helper(session, FilingDAO, filing_period=filing_period)
    return filings


def get_filing_period(session: Session, filing_period: str) -> FilingPeriodDAO:
    result = query_helper(session, FilingPeriodDAO, code=filing_period)
    return result[0] if result else None


@lru_cache(maxsize=128)
def get_filing_tasks(session: Session) -> List[FilingTaskDAO]:
    return query_helper(session, FilingTaskDAO)


def get_user_action(session: Session, id: int) -> UserActionDAO:
    result = query_helper(session, UserActionDAO, id=id)
    return result[0] if result else None


def get_user_actions(session: Session) -> List[UserActionDAO]:
    return query_helper(session, UserActionDAO)


def add_submission(session: Session, filing_id: int, filename: str, submitter_id: int) -> SubmissionDAO:
    stmt = select(SubmissionDAO).filter_by(filing=filing_id).order_by(desc(SubmissionDAO.counter)).limit(1)
    last_sub = session.scalar(stmt)
    current_count = last_sub.counter if last_sub else 0
    new_sub = SubmissionDAO(
        filing=filing_id,
        state=SubmissionState.SUBMISSION_STARTED,
        filename=filename,
        submitter_id=submitter_id,
        counter=(current_count + 1),
    )
    # this returns the attached object, most importantly with the new submission id
    new_sub = session.merge(new_sub)
    session.commit()
    return new_sub


def update_submission(session: Session, submission: SubmissionDAO) -> SubmissionDAO:
    return upsert_helper(session, submission, SubmissionDAO)


def expire_submission(submission_id: int):
    with SessionLocal() as session:
        submission = get_submission(session, submission_id)
        submission.state = SubmissionState.VALIDATION_EXPIRED
        upsert_helper(session, submission, SubmissionDAO)


def error_out_submission(submission_id: int):
    with SessionLocal() as session:
        submission = get_submission(session, submission_id)
        submission.state = SubmissionState.VALIDATION_ERROR
        upsert_helper(session, submission, SubmissionDAO)


def upsert_filing_period(session: Session, filing_period: FilingPeriodDTO) -> FilingPeriodDAO:
    return upsert_helper(session, filing_period, FilingPeriodDAO)


def upsert_filing(session: Session, filing: FilingDTO) -> FilingDAO:
    return upsert_helper(session, filing, FilingDAO)


def create_new_filing(session: Session, lei: str, filing_period: str, creator_id: int) -> FilingDAO:
    new_filing = FilingDAO(filing_period=filing_period, lei=lei, creator_id=creator_id)
    return upsert_helper(session, new_filing, FilingDAO)


def update_task_state(
    session: Session, lei: str, filing_period: str, task_name: str, state: FilingTaskState, user: AuthenticatedUser
):
    filing = get_filing(session, lei=lei, filing_period=filing_period)
    found_task = query_helper(session, FilingTaskProgressDAO, filing=filing.id, task_name=task_name)
    if found_task:
        task = found_task[0]  # should only be one
        task.state = state
        task.user = user.username
    else:
        task = FilingTaskProgressDAO(filing=filing.id, state=state, task_name=task_name, user=user.username)
    upsert_helper(session, task, FilingTaskProgressDAO)


def update_contact_info(session: Session, lei: str, filing_period: str, new_contact_info: ContactInfoDTO) -> FilingDAO:
    filing = get_filing(session, lei=lei, filing_period=filing_period)
    if filing.contact_info:
        for key, value in new_contact_info.__dict__.items():
            if key != "id":
                setattr(filing.contact_info, key, value)
    else:
        filing.contact_info = ContactInfoDAO(**new_contact_info.__dict__.copy(), filing=filing.id)
    return upsert_helper(session, filing, FilingDAO)


def add_user_action(
    session: Session,
    new_user_action: UserActionDTO,
) -> UserActionDAO:
    return upsert_helper(session, new_user_action, UserActionDAO)


def upsert_helper(session: Session, original_data: Any, table_obj: T) -> T:
    copy_data = original_data.__dict__.copy()
    # this is only for if a DAO is passed in
    # Should be DTOs, but hey, it's python
    if "_sa_instance_state" in copy_data:
        del copy_data["_sa_instance_state"]
    new_dao = table_obj(**copy_data)
    new_dao = session.merge(new_dao)
    session.commit()
    session.refresh(new_dao)
    return new_dao


def query_helper(session: Session, table_obj: T, **filter_args) -> List[T]:
    stmt = select(table_obj)
    # remove empty args
    filter_args = {k: v for k, v in filter_args.items() if v is not None}
    if filter_args:
        stmt = stmt.filter_by(**filter_args)
    return (session.scalars(stmt)).all()
