from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, ConfigDict
from .model_enums import FilingType, FilingState, SubmissionState


class SubmissionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    submitter: str
    state: SubmissionState | None = None
    validation_ruleset_version: str | None = None
    validation_json: Dict[str, Any] | None = None
    filing: int
    confirmation_id: str | None = None


class FilingDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    lei: str
    state: FilingState
    filing_period: int
    institution_snapshot_id: str
    contact_info: str


class FilingPeriodDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    name: str
    start_period: datetime
    end_period: datetime
    due: datetime
    filing_type: FilingType
