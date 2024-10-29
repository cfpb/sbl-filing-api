from sbl_filing_api.config import regex_configs
from datetime import datetime
from typing import Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sbl_filing_api.entities.models.model_enums import FilingType, FilingTaskState, SubmissionState, UserActionType


class UserActionDTO(BaseModel):
    id: int | None = None
    user_id: str = Field(max_length=36)
    user_name: str = Field(max_length=255)
    user_email: str = Field(max_length=255)
    timestamp: datetime | None = None
    action_type: UserActionType


class SubmissionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    counter: int
    state: SubmissionState | None = None
    validation_ruleset_version: str | None = None
    validation_results: Dict[str, Any] | None = None
    submission_time: datetime | None = None
    filename: str
    total_records: int | None = None
    submitter: UserActionDTO
    accepter: UserActionDTO | None = None


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
    first_name: str = Field(max_length=255)
    last_name: str = Field(max_length=255)
    hq_address_street_1: str = Field(max_length=255)
    hq_address_street_2: str | None = Field(None, max_length=255)
    hq_address_street_3: str | None = Field(None, max_length=255)
    hq_address_street_4: str | None = Field(None, max_length=255)
    hq_address_city: str = Field(max_length=255)
    hq_address_state: str = Field(max_length=255)
    hq_address_zip: str = Field(max_length=5)
    email: str = Field(max_length=255)
    phone_number: str = Field(max_length=255)
    phone_ext: str | None = Field(None, max_length=255)

    @model_validator(mode="after")
    def validate_fi(self) -> "ContactInfoDTO":
        if self.email:
            match = regex_configs.email.regex.match(self.email)
            if not match:
                raise ValueError(f"Invalid email {self.email}. {regex_configs.email.error_text}")
        if self.phone_number:
            match = regex_configs.phone_number.regex.match(self.phone_number)
            if not match:
                raise ValueError(f"Invalid phone number {self.phone_number}. {regex_configs.phone_number.error_text}")
        return self


class FilingDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filing_period: str
    lei: str
    tasks: List[FilingTaskProgressDTO] | None = Field(None, deprecated=True)
    institution_snapshot_id: str | None = None
    contact_info: ContactInfoDTO | None = None
    confirmation_id: str | None = None
    signatures: List[UserActionDTO] = []
    creator: UserActionDTO
    is_voluntary: bool | None = None


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


class VoluntaryUpdateDTO(BaseModel):
    model_config = ConfigDict(from_attribute=True)

    is_voluntary: bool
