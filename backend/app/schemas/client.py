"""Pydantic schemas for clients."""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ClientBase(BaseModel):
    fname: str = Field(..., min_length=1, max_length=50)
    lname: str = Field(..., min_length=1, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = None
    sex: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, v):
        if v is not None and v not in ("M", "F", "O"):
            raise ValueError("sex must be M, F, or O")
        return v


class ClientCreate(ClientBase):
    phone_numbers: Optional[List[str]] = []


class ClientUpdate(BaseModel):
    fname: Optional[str] = Field(None, min_length=1, max_length=50)
    lname: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[str] = None
    address: Optional[str] = None
    sex: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, v):
        if v is not None and v not in ("M", "F", "O"):
            raise ValueError("sex must be M, F, or O")
        return v

    @field_validator("fname", "lname")
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


class ClientResponse(ClientBase):
    client_id: int
    model_config = ConfigDict(from_attributes=True)


class ClientDetailed(ClientResponse):
    phone_numbers: List[str] = []
    total_cases: int = 0
    active_cases: int = 0
    disposed_cases: int = 0
    recent_cases: List[CaseBrief] = []
    model_config = ConfigDict(from_attributes=True)


class ClientList(BaseModel):
    client_id: int
    fname: str
    lname: str
    email: Optional[str] = None
    notes: Optional[str] = None
    total_cases: int = 0
    can_open: bool = True
    model_config = ConfigDict(from_attributes=True)


class PaginatedClients(BaseModel):
    items: List[ClientList]
    total: int
    page: int
    size: int
    pages: int
