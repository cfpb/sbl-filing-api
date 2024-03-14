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
    submission_time: datetime | None = None
    filename: str


class FilingTaskDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    task_order: int


class FilingTaskProgressDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    task: FilingTaskDTO
    user: str | None = None
    state: FilingTaskState
    change_timestamp: datetime | None = None


class ContactInfoDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    first_name: str
    last_name: str
    hq_address_street_1: str
    hq_address_street_2: str | None = None
    hq_address_city: str
    hq_address_state: str
    hq_address_zip: str
    email: str
    phone: str


class FilingDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filing_period: str
    lei: str
    tasks: List[FilingTaskProgressDTO] | None = None
    institution_snapshot_id: str
    contact_info: ContactInfoDTO | None = None
    confirmation_id: str | None = None


class FilingPeriodDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    description: str
    start_period: datetime
    end_period: datetime
    due: datetime
    filing_type: FilingType


class SnapshotUpdateDTO(BaseModel):
    model_config = ConfigDict(from_attribute=True)

    institution_snapshot_id: str


class StateUpdateDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    state: FilingTaskState
