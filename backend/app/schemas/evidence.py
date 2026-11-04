"""Pydantic schemas for evidence metadata."""
from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field, ConfigDict, field_validator


EVIDENCE_STATUSES = ["Received", "Under Review", "Filed", "Produced"]


class EvidenceBase(BaseModel):
    description: Optional[str] = None
    filed_date: date
    status: str = Field(default="Received")
    lawyer_id: Optional[int] = None
    case_id: int

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in EVIDENCE_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(EVIDENCE_STATUSES)}")
        return v


class EvidenceCreate(EvidenceBase):
    pass


class EvidenceUpdate(BaseModel):
    description: Optional[str] = None
    filed_date: Optional[date] = None
    status: Optional[str] = None
    lawyer_id: Optional[int] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in EVIDENCE_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(EVIDENCE_STATUSES)}")
        return v

    @field_validator("filed_date")
    @classmethod
    def not_null(cls, v):
        if v is None:
            raise ValueError("cannot be null")
        return v


class LawyerBrief(BaseModel):
    lawyer_id: int
    fname: str
    lname: str
    designation: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class CaseBrief(BaseModel):
    case_id: int
    matter_title: str
    case_number: str
    status: str
    model_config = ConfigDict(from_attributes=True)


class FileInfo(BaseModel):
    filename: str
    content_type: str
    size: int
    upload_date: str
    mongo_id: str


class EvidenceResponse(EvidenceBase):
    evidence_id: int
    mongo_id: Optional[str] = None
    lawyer: Optional[LawyerBrief] = None
    legal_case: Optional[CaseBrief] = None
    has_file: bool = False
    model_config = ConfigDict(from_attributes=True)


class EvidenceDetailed(EvidenceResponse):
    file_info: Optional[FileInfo] = None
    model_config = ConfigDict(from_attributes=True)


class EvidenceList(BaseModel):
    evidence_id: int
    description: Optional[str] = None
    filed_date: date
    status: str
    case_title: Optional[str] = None
    lawyer_name: Optional[str] = None
    has_file: bool = False
    model_config = ConfigDict(from_attributes=True)


class PaginatedEvidence(BaseModel):
    items: List[EvidenceList]
    total: int
    page: int
    size: int
    pages: int
