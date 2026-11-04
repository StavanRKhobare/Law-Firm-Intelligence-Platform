"""Pydantic schemas for legal matters."""
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


MATTER_STATUSES = ["Filed", "Hearing", "Pending", "Disposed"]
ASSIGNMENT_ROLES = ["Lead Counsel", "Associate", "Research"]
OUTCOMES = ["Won", "Lost", "Settled", "Withdrawn", "Dismissed", "Other"]


def not_in_future(v):
    if v is not None and v > date.today():
        raise ValueError("Date cannot be in the future")
    return v


class MatterTypeSchema(BaseModel):
    matter_type: str
    model_config = ConfigDict(from_attributes=True)


class StatuteSectionSchema(BaseModel):
    statute_section: str
    model_config = ConfigDict(from_attributes=True)


class AssignmentCreate(BaseModel):
    lawyer_id: int
    role: str
    assigned_date: date = Field(default_factory=date.today)
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
    case_number: str = Field(..., min_length=1, max_length=50)
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
    _dates_not_future = field_validator("date_cause", "date_filed")(not_in_future)

    matter_types: Optional[List[str]] = []
    statute_sections: Optional[List[str]] = []
    client_ids: Optional[List[int]] = []
    party_ids: Optional[List[int]] = []
    assignments: Optional[List[AssignmentCreate]] = []


class LegalCaseUpdate(BaseModel):
    matter_title: Optional[str] = Field(None, min_length=3, max_length=200)
    case_number: Optional[str] = Field(None, min_length=1, max_length=50)
    matter_description: Optional[str] = None
    date_cause: Optional[date] = None
    date_filed: Optional[date] = None
    status: Optional[str] = None
    court_id: Optional[int] = None
    location_id: Optional[int] = None
    # When given, each list replaces what the matter has now
    matter_types: Optional[List[str]] = None
    statute_sections: Optional[List[str]] = None
    client_ids: Optional[List[int]] = None
    party_ids: Optional[List[int]] = None

    _dates_not_future = field_validator("date_cause", "date_filed")(not_in_future)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in MATTER_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(MATTER_STATUSES)}")
        return v

    @field_validator("matter_title", "case_number", "date_cause", "date_filed")
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


class CourtCreate(BaseModel):
    court_name: str = Field(..., min_length=1, max_length=200)
    court_type: str = Field(..., min_length=1, max_length=50)
    pincode: Optional[str] = Field(None, max_length=10)
    city: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)


class LocationCreate(BaseModel):
    landmark: str = Field(..., min_length=1, max_length=200)
    streetno: Optional[str] = Field(None, max_length=50)
    pincode: Optional[str] = Field(None, max_length=10)
    city: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)


class LocationResponse(BaseModel):
    location_id: int
    landmark: Optional[str] = None
    streetno: Optional[str] = None
    pincode: Optional[str] = None
    city: Optional[str] = None


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


class CasePermissions(BaseModel):
    view: bool = False
    work: bool = False
    edit: bool = False
    assign: bool = False
    delete: bool = False


class LegalCaseResponse(LegalCaseBase):
    case_id: int
    disposed_on: Optional[date] = None
    outcome: Optional[str] = None
    next_hearing: Optional[date] = None
    assignments: List[AssignmentResponse] = []
    permissions: CasePermissions = CasePermissions()
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
    date_filed: Optional[date] = None
    lead_counsel: Optional[str] = None
    court_name: Optional[str] = None
    location_name: Optional[str] = None
    matter_types: List[str] = []
    next_hearing: Optional[date] = None
    # False: the user sees only the title and number of this matter
    can_open: bool = True
    model_config = ConfigDict(from_attributes=True)


class PaginatedLegalCases(BaseModel):
    items: List[LegalCaseList]
    total: int
    page: int
    size: int
    pages: int


class TimelineEvent(BaseModel):
    at: datetime
    kind: str
    title: str
    detail: Optional[str] = None
    actor: Optional[str] = None
    upcoming: bool = False


class NoteCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=10000)


class NoteResponse(BaseModel):
    note_id: int
    case_id: int
    body: str
    author_id: Optional[int] = None
    author_name: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
