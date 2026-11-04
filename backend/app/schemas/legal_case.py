"""Pydantic schemas for legal matters."""
from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


MATTER_STATUSES = ["Filed", "Hearing", "Pending", "Disposed"]
ASSIGNMENT_ROLES = ["Lead Counsel", "Associate", "Research"]


class MatterTypeSchema(BaseModel):
    matter_type: str
    model_config = ConfigDict(from_attributes=True)


class StatuteSectionSchema(BaseModel):
    statute_section: str
    model_config = ConfigDict(from_attributes=True)


class AssignmentCreate(BaseModel):
    lawyer_id: int
    role: str
    assigned_date: date
    end_date: Optional[date] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ASSIGNMENT_ROLES:
            raise ValueError(f"Role must be one of: {', '.join(ASSIGNMENT_ROLES)}")
        return v

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date and self.end_date < self.assigned_date:
            raise ValueError("End date cannot be before the assigned date")
        return self


class AssignmentResponse(AssignmentCreate):
    lawyer_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class LegalCaseBase(BaseModel):
    matter_title: str = Field(..., min_length=3, max_length=200)
    matter_description: Optional[str] = None
    case_number: str
    date_cause: date
    date_filed: date
    status: str = Field(default="Filed")
    court_id: Optional[int] = None
    location_id: Optional[int] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in MATTER_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(MATTER_STATUSES)}")
        return v

    @model_validator(mode="after")
    def validate_dates(self):
        if self.date_cause and self.date_filed and self.date_filed < self.date_cause:
            raise ValueError("Filing date cannot be before the cause of action")
        return self


class LegalCaseCreate(LegalCaseBase):
    matter_types: Optional[List[str]] = []
    statute_sections: Optional[List[str]] = []
    client_ids: Optional[List[int]] = []
    party_ids: Optional[List[int]] = []
    assignments: Optional[List[AssignmentCreate]] = []


class LegalCaseUpdate(BaseModel):
    matter_title: Optional[str] = Field(None, min_length=3, max_length=200)
    matter_description: Optional[str] = None
    date_cause: Optional[date] = None
    date_filed: Optional[date] = None
    status: Optional[str] = None
    court_id: Optional[int] = None
    location_id: Optional[int] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in MATTER_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(MATTER_STATUSES)}")
        return v

    @field_validator("matter_title", "date_cause", "date_filed")
    @classmethod
    def not_null(cls, v):
        if v is None:
            raise ValueError("cannot be null")
        return v


class CourtBrief(BaseModel):
    court_id: int
    court_name: str
    court_type: str
    model_config = ConfigDict(from_attributes=True)


class LocationBrief(BaseModel):
    location_id: int
    landmark: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ClientBrief(BaseModel):
    client_id: int
    fname: str
    lname: str
    notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class PartyBrief(BaseModel):
    party_id: int
    fname: str
    lname: str
    repeat_party: bool
    model_config = ConfigDict(from_attributes=True)


class LegalCaseResponse(LegalCaseBase):
    case_id: int
    matter_types: List[MatterTypeSchema] = []
    statute_sections: List[StatuteSectionSchema] = []
    court: Optional[CourtBrief] = None
    location: Optional[LocationBrief] = None
    clients: List[ClientBrief] = []
    opposing_parties: List[PartyBrief] = []
    model_config = ConfigDict(from_attributes=True)


class LegalCaseList(BaseModel):
    case_id: int
    matter_title: str
    case_number: str
    status: str
    date_cause: date
    lead_counsel: Optional[str] = None
    court_name: Optional[str] = None
    location_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class PaginatedLegalCases(BaseModel):
    items: List[LegalCaseList]
    total: int
    page: int
    size: int
    pages: int
