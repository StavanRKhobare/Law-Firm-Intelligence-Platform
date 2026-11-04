"""Pydantic schemas for opposing parties."""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator


class PartyBase(BaseModel):
    fname: str = Field(..., min_length=1, max_length=50)
    lname: str = Field(..., min_length=1, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = None
    sex: Optional[str] = None
    repeat_party: bool = False

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, v):
        if v is not None and v not in ("M", "F", "O"):
            raise ValueError("sex must be M, F, or O")
        return v


class PartyCreate(PartyBase):
    phone_numbers: Optional[List[str]] = []


class PartyUpdate(BaseModel):
    fname: Optional[str] = Field(None, min_length=1, max_length=50)
    lname: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[str] = None
    address: Optional[str] = None
    sex: Optional[str] = None
    repeat_party: Optional[bool] = None

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, v):
        if v is not None and v not in ("M", "F", "O"):
            raise ValueError("sex must be M, F, or O")
        return v

    @field_validator("fname", "lname", "repeat_party")
    @classmethod
    def not_null(cls, v):
        if v is None:
            raise ValueError("cannot be null")
        return v


class CaseBrief(BaseModel):
    case_id: int
    matter_title: str
    case_number: str
    status: str
    model_config = ConfigDict(from_attributes=True)


class PartyResponse(PartyBase):
    party_id: int
    model_config = ConfigDict(from_attributes=True)


class PartyDetailed(PartyResponse):
    phone_numbers: List[str] = []
    total_cases: int = 0
    active_cases: int = 0
    disposed_cases: int = 0
    recent_cases: List[CaseBrief] = []
    model_config = ConfigDict(from_attributes=True)


class PartyList(BaseModel):
    party_id: int
    fname: str
    lname: str
    email: Optional[str] = None
    repeat_party: bool = False
    total_cases: int = 0
    model_config = ConfigDict(from_attributes=True)


class PaginatedParties(BaseModel):
    items: List[PartyList]
    total: int
    page: int
    size: int
    pages: int
