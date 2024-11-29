from sbl_filing_api.entities.models.model_enums import FilingType, FilingTaskState, SubmissionState, UserActionType
from datetime import datetime
from typing import Any, List
from sqlalchemy import Enum as SAEnum, String, desc
from sqlalchemy import ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.types import JSON


class Base(AsyncAttrs, DeclarativeBase):
    pass


class UserActionDAO(Base):
    __tablename__ = "user_action"
    id: Mapped[int] = mapped_column(index=True, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36))
    user_name: Mapped[str] = mapped_column(String(255))
    user_email: Mapped[str] = mapped_column(String(255))
    action_type: Mapped[UserActionType] = mapped_column(SAEnum(UserActionType))
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now())


class SubmissionDAO(Base):
    __tablename__ = "submission"
    id: Mapped[int] = mapped_column(index=True, primary_key=True, autoincrement=True)
    filing: Mapped[int] = mapped_column(ForeignKey("filing.id"))
    counter: Mapped[int]
    submitter_id: Mapped[int] = mapped_column(ForeignKey("user_action.id"))
    submitter: Mapped[UserActionDAO] = relationship(lazy="selectin", foreign_keys=[submitter_id])
    accepter_id: Mapped[int] = mapped_column(ForeignKey("user_action.id"), nullable=True)
    accepter: Mapped[UserActionDAO] = relationship(lazy="selectin", foreign_keys=[accepter_id])
    state: Mapped[SubmissionState] = mapped_column(SAEnum(SubmissionState))
    validation_ruleset_version: Mapped[str] = mapped_column(nullable=True)
    validation_results: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=True)
    submission_time: Mapped[datetime] = mapped_column(server_default=func.now())
    filename: Mapped[str]
    total_records: Mapped[int] = mapped_column(nullable=True)

    __table_args__ = (UniqueConstraint("filing", "counter", name="unique_filing_counter"),)

    def __str__(self):
        return f"Submission ID: {self.id}, Counter: {self.counter}, State: {self.state}, Ruleset: {self.validation_ruleset_version}, Filing Period: {self.filing}, Submission: {self.submission_time}"


class FilingPeriodDAO(Base):
    __tablename__ = "filing_period"
    code: Mapped[str] = mapped_column(primary_key=True)
    description: Mapped[str]
    start_period: Mapped[datetime]
    end_period: Mapped[datetime]
    due: Mapped[datetime]
    filing_type: Mapped[FilingType] = mapped_column(SAEnum(FilingType))


class FilingTaskDAO(Base):
    __tablename__ = "filing_task"
    name: Mapped[str] = mapped_column(primary_key=True)
    task_order: Mapped[int]

    def __str__(self):
        return f"Name: {self.name}, Order: {self.task_order}"


class FilingTaskProgressDAO(Base):
    __tablename__ = "filing_task_progress"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filing: Mapped[int] = mapped_column(ForeignKey("filing.id"))
    task_name: Mapped[str] = mapped_column(ForeignKey("filing_task.name"))
    task: Mapped[FilingTaskDAO] = relationship(lazy="selectin")
    user: Mapped[str]
    state: Mapped[FilingTaskState] = mapped_column(SAEnum(FilingTaskState))
    change_timestamp: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    def __str__(self):
        return f"ID: {self.id},Filing ID: {self.filing}, Task: {self.task}, User: {self.user}, state: {self.state}, Timestamp: {self.change_timestamp}"


class ContactInfoDAO(Base):
    __tablename__ = "contact_info"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filing: Mapped[int] = mapped_column(ForeignKey("filing.id"))
    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str] = mapped_column(String(255))
    hq_address_street_1: Mapped[str] = mapped_column(String(255))
    hq_address_street_2: Mapped[str] = mapped_column(String(255), nullable=True)
    hq_address_street_3: Mapped[str] = mapped_column(String(255), nullable=True)
    hq_address_street_4: Mapped[str] = mapped_column(String(255), nullable=True)
    hq_address_city: Mapped[str] = mapped_column(String(255))
    hq_address_state: Mapped[str] = mapped_column(String(255))
    hq_address_zip: Mapped[str] = mapped_column(String(5))
    email: Mapped[str] = mapped_column(String(255))
    phone_number: Mapped[str] = mapped_column(String(255))
    phone_ext: Mapped[str] = mapped_column(String(255), nullable=True)

    def __str__(self):
        return f"ContactInfo ID: {self.id}, First Name: {self.first_name}, Last Name: {self.last_name}, Address Street 1: {self.hq_address_street_1}, Address Street 2: {self.hq_address_street_2}, Address City: {self.hq_address_city}, Address State: {self.hq_address_state}, Address Zip: {self.hq_address_zip}"


class FilingSignatureDAO(Base):
    __tablename__ = "filing_signature"
    user_action: Mapped[int] = mapped_column(
        ForeignKey("user_action.id"), nullable=False, primary_key=True, unique=True
    )
    filing: Mapped[int] = mapped_column(ForeignKey("filing.id"), index=True, nullable=False)


class FilingDAO(Base):
    __tablename__ = "filing"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filing_period: Mapped[str] = mapped_column(ForeignKey("filing_period.code"))
    lei: Mapped[str]
    tasks: Mapped[List[FilingTaskProgressDAO] | None] = relationship(lazy="selectin", cascade="all, delete-orphan")
    institution_snapshot_id: Mapped[str] = mapped_column(nullable=True)
    contact_info: Mapped[ContactInfoDAO | None] = relationship("ContactInfoDAO", lazy="joined")
    submissions: Mapped[List[SubmissionDAO] | None] = relationship(
        "SubmissionDAO", lazy="select", order_by=desc(SubmissionDAO.submission_time)
    )
    signatures: Mapped[List[UserActionDAO] | None] = relationship(
        "UserActionDAO", secondary="filing_signature", lazy="selectin", order_by="desc(UserActionDAO.timestamp)"
    )
    confirmation_id: Mapped[str] = mapped_column(nullable=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("user_action.id"))
    creator: Mapped[UserActionDAO] = relationship(lazy="selectin", foreign_keys=[creator_id])
    is_voluntary: Mapped[bool] = mapped_column(nullable=True)

    def __str__(self):
        return f"ID: {self.id}, Filing Period: {self.filing_period}, LEI: {self.lei}, Tasks: {self.tasks}, Institution Snapshot ID: {self.institution_snapshot_id}, Contact Info: {self.contact_info}"


# Commenting out for now since we're just storing the results from the data-validator as JSON.
# If we determine building the data structure for results as tables is needed, we can add these
# back in.
# class FindingDAO(Base):
#    __tablename__ = "submission_finding"
#    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
#    submission_id: Mapped[str] = mapped_column(ForeignKey("submission.id"))
#    submission: Mapped["SubmissionDAO"] = relationship(back_populates="results")  # if we care about bidirectional
#    validation_code: Mapped[str]
#    severity: Mapped[Severity] = mapped_column(Enum(*get_args(Severity)))
#    records: Mapped[List["RecordDAO"]] = relationship(back_populates="result")


# class RecordDAO(Base):
#    __tablename__ = "submission_finding_record"
#    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
#    result_id: Mapped[str] = mapped_column(ForeignKey("submission_finding.id"))
#    result: Mapped["FindingDAO"] = relationship(back_populates="records")  # if we care about bidirectional
#    record: Mapped[int]
#    field_name: Mapped[str]
#    field_value: Mapped[str]
