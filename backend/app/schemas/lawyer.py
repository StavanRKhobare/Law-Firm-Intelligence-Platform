"""Pydantic schemas for lawyers and practice groups."""
from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator


class PracticeGroupBrief(BaseModel):
    group_id: int
    group_name: str
    model_config = ConfigDict(from_attributes=True)


class PracticeGroupCreate(BaseModel):
    group_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    email: Optional[str] = Field(None, max_length=100)
    contactno: Optional[str] = Field(None, max_length=15)


class LawyerBase(BaseModel):
    fname: str = Field(..., min_length=1, max_length=50)
    lname: str = Field(..., min_length=1, max_length=50)
    designation: Optional[str] = Field(None, max_length=50)
    phoneno: Optional[str] = Field(None, max_length=15)
    bar_id: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    joined_date: Optional[date] = None
    group_id: Optional[int] = None


class LawyerCreate(LawyerBase):
    pass


class LawyerUpdate(BaseModel):
    fname: Optional[str] = Field(None, min_length=1, max_length=50)
    lname: Optional[str] = Field(None, min_length=1, max_length=50)
    designation: Optional[str] = Field(None, max_length=50)
    phoneno: Optional[str] = Field(None, max_length=15)
    bar_id: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    joined_date: Optional[date] = None
    group_id: Optional[int] = None

    @field_validator("fname", "lname")
    @classmethod
    def not_null(cls, v):
        # Optional here means "may be left out", not "may be set to null" (the columns are NOT NULL)
        if v is None:
            raise ValueError("cannot be null")
        return v


class CaseBrief(BaseModel):
    case_id: int
    matter_title: str
    case_number: str
    status: str
    role: Optional[str] = None
    assigned_date: Optional[date] = None
    model_config = ConfigDict(from_attributes=True)


class LawyerResponse(LawyerBase):
    lawyer_id: int
    is_active: bool = True
    practice_group: Optional[PracticeGroupBrief] = None
    model_config = ConfigDict(from_attributes=True)


class LawyerDetailed(LawyerResponse):
    total_cases: int = 0
    active_cases: int = 0
    disposed_cases: int = 0
    upcoming_hearings: int = 0
    overdue_tasks: int = 0
    has_login: bool = False
    # False: the user sees this colleague's public profile, without their matters
    can_view_matters: bool = False
    matters: List[CaseBrief] = []
    model_config = ConfigDict(from_attributes=True)


class LawyerList(BaseModel):
    lawyer_id: int
    fname: str
    lname: str
    designation: Optional[str] = None
    group_name: Optional[str] = None
    total_cases: int = 0
    is_active: bool = True
    has_login: bool = False
    model_config = ConfigDict(from_attributes=True)


class PaginatedLawyers(BaseModel):
    items: List[LawyerList]
    total: int
    page: int
    size: int
    pages: int
