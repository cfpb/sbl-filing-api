from .model_enums import FilingType, FilingTaskState, SubmissionState
from datetime import datetime
from typing import Any, List
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, func, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.types import JSON


class Base(AsyncAttrs, DeclarativeBase):
    pass


class SubmissionDAO(Base):
    __tablename__ = "submission"
    id: Mapped[int] = mapped_column(index=True, primary_key=True, autoincrement=True)
    submitter: Mapped[str]
    state: Mapped[SubmissionState] = mapped_column(SAEnum(SubmissionState))
    validation_ruleset_version: Mapped[str] = mapped_column(nullable=True)
    validation_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=True)
    filing_period: Mapped[str]
    lei: Mapped[str]
    confirmation_id: Mapped[str] = mapped_column(nullable=True)
    
    __table_args__ = (
            ForeignKeyConstraint(["filing_period", "lei"],["filing.filing_period","filing.lei"]))

    def __str__(self):
        return f"Submission ID: {self.id}, Submitter: {self.submitter}, State: {self.state}, Ruleset: {self.validation_ruleset_version}, Filing: {self.filing}"


class FilingPeriodDAO(Base):
    __tablename__ = "filing_period"
    name: Mapped[str] = mapped_column(primary_key=True)
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


class FilingTaskStateDAO(Base):
    __tablename__ = "filing_task_state"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filing_period: Mapped[str]
    lei: Mapped[str]
    task_name: Mapped[str] = mapped_column(ForeignKey("filing_task.name"))
    task: Mapped[FilingTaskDAO] = relationship(lazy="selectin")
    user: Mapped[str]
    state: Mapped[FilingTaskState] = mapped_column(SAEnum(FilingTaskState))
    change_timestamp: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
            ForeignKeyConstraint(["filing_period", "lei"],["filing.filing_period","filing.lei"]))

    def __str__(self):
        return f"Filing ID: {self.filing}, Task: {self.task}, User: {self.user}, state: {self.state}, Timestamp: {self.change_timestamp}"


class FilingDAO(Base):
    __tablename__ = "filing"
    filing_period: Mapped[str] = mapped_column(ForeignKey("filing_period.name"), primary_key=True)
    lei: Mapped[str] = mapped_column(primary_key=True)
    tasks: Mapped[List[FilingTaskStateDAO]] = relationship(lazy="selectin", cascade="all, delete-orphan")
    institution_snapshot_id: Mapped[str]
    contact_info: Mapped[str] = mapped_column(nullable=True)


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
