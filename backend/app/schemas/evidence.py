"""Pydantic schemas for documents and evidence. File bytes are in MongoDB, metadata here."""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

EVIDENCE_STATUSES = ["Received", "Under Review", "Filed", "Produced"]
DOCUMENT_CATEGORIES = ["Evidence", "Pleading", "Order", "Correspondence", "Draft", "Other"]


class EvidenceUpdate(BaseModel):
    description: Optional[str] = None
    filed_date: Optional[date] = None
    status: Optional[str] = None
    category: Optional[str] = None
    lawyer_id: Optional[int] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in EVIDENCE_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(EVIDENCE_STATUSES)}")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        if v not in DOCUMENT_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(DOCUMENT_CATEGORIES)}")
        return v

    @field_validator("filed_date")
    @classmethod
    def not_null(cls, v):
        if v is None:
            raise ValueError("cannot be null")
        return v


class EvidenceResponse(BaseModel):
    evidence_id: int
    case_id: int
    case_number: Optional[str] = None
    case_title: Optional[str] = None
    description: Optional[str] = None
    filed_date: date
    status: str
    category: str
    lawyer_id: Optional[int] = None
    lawyer_name: Optional[str] = None
    has_file: bool = False
    file_name: Optional[str] = None
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class PaginatedEvidence(BaseModel):
    items: List[EvidenceResponse]
    total: int
    page: int
    size: int
    pages: int
