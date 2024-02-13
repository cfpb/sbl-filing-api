from datetime import datetime
from typing import Dict, Any, List
from pydantic import BaseModel, ConfigDict
from .model_enums import FilingType, FilingTaskState, SubmissionState


class SubmissionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    submitter: str
    state: SubmissionState | None = None
    validation_ruleset_version: str | None = None
    validation_json: Dict[str, Any] | None = None
    filing_period: str
    lei: str
    confirmation_id: str | None = None
    submission_time: datetime | None = None


class FilingTaskDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    task_order: int


class FilingTaskStateDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    filing_period: str
    lei: str
    task: FilingTaskDTO
    user: str | None = None
    state: FilingTaskState
    change_timestamp: datetime | None = None


class FilingDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    filing_period: str
    lei: str
    tasks: List[FilingTaskStateDTO]
    institution_snapshot_id: str
    contact_info: str | None = None


class FilingPeriodDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    start_period: datetime
    end_period: datetime
    due: datetime
    filing_type: FilingType
