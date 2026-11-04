"""Schemas for hearings, tasks, and the daily workspace."""
from datetime import date, datetime, time
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

HEARING_STATUSES = ["Scheduled", "Held", "Adjourned", "Cancelled"]
TASK_KINDS = ["Task", "Limitation", "Filing", "Compliance", "Reply"]
TASK_PRIORITIES = ["Low", "Normal", "High"]
TASK_STATUSES = ["Open", "In Progress", "Done"]


def one_of(value, allowed):
    if value is not None and value not in allowed:
        raise ValueError(f"Must be one of: {', '.join(allowed)}")
    return value


class HearingCreate(BaseModel):
    case_id: int
    hearing_date: date
    hearing_time: Optional[time] = None
    court_id: Optional[int] = None
    courtroom: Optional[str] = Field(None, max_length=50)
    judge: Optional[str] = Field(None, max_length=100)
    purpose: Optional[str] = Field(None, max_length=200)
    status: str = "Scheduled"
    outcome: Optional[str] = None
    remarks: Optional[str] = None
    attended_by: Optional[int] = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        return one_of(v, HEARING_STATUSES)


class HearingUpdate(BaseModel):
    hearing_date: Optional[date] = None
    hearing_time: Optional[time] = None
    court_id: Optional[int] = None
    courtroom: Optional[str] = Field(None, max_length=50)
    judge: Optional[str] = Field(None, max_length=100)
    purpose: Optional[str] = Field(None, max_length=200)
    outcome: Optional[str] = None
    remarks: Optional[str] = None
    attended_by: Optional[int] = None

    @field_validator("hearing_date")
    @classmethod
    def date_not_null(cls, v):
        if v is None:
            raise ValueError("cannot be null")
        return v


class HearingResult(BaseModel):
    """What happened at a hearing, and optionally the next date."""
    status: str
    outcome: Optional[str] = None
    remarks: Optional[str] = None
    attended_by: Optional[int] = None
    next_date: Optional[date] = None
    next_purpose: Optional[str] = Field(None, max_length=200)

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        if v not in ("Held", "Adjourned", "Cancelled"):
            raise ValueError("Must be Held, Adjourned or Cancelled")
        return v


class HearingResponse(BaseModel):
    hearing_id: int
    case_id: int
    case_number: Optional[str] = None
    matter_title: Optional[str] = None
    lead_counsel: Optional[str] = None
    hearing_date: date
    hearing_time: Optional[time] = None
    court_id: Optional[int] = None
    court_name: Optional[str] = None
    courtroom: Optional[str] = None
    judge: Optional[str] = None
    purpose: Optional[str] = None
    status: str
    outcome: Optional[str] = None
    remarks: Optional[str] = None
    attended_by: Optional[int] = None
    attended_by_name: Optional[str] = None
    can_work: bool = True


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    kind: str = "Task"
    priority: str = "Normal"
    due_date: Optional[date] = None
    case_id: Optional[int] = None
    assignee_id: Optional[int] = None

    @field_validator("kind")
    @classmethod
    def valid_kind(cls, v):
        return one_of(v, TASK_KINDS)

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v):
        return one_of(v, TASK_PRIORITIES)

    @model_validator(mode="after")
    def deadline_needs_date(self):
        if self.kind != "Task" and self.due_date is None:
            raise ValueError("A legal deadline needs a due date")
        return self


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    kind: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[date] = None
    assignee_id: Optional[int] = None

    @field_validator("kind")
    @classmethod
    def valid_kind(cls, v):
        return one_of(v, TASK_KINDS)

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v):
        return one_of(v, TASK_PRIORITIES)

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        return one_of(v, TASK_STATUSES)

    @field_validator("title", "kind", "priority", "status")
    @classmethod
    def not_null(cls, v):
        if v is None:
            raise ValueError("cannot be null")
        return v


class TaskResponse(BaseModel):
    task_id: int
    title: str
    description: Optional[str] = None
    kind: str
    priority: str
    status: str
    due_date: Optional[date] = None
    overdue: bool = False
    case_id: Optional[int] = None
    case_number: Optional[str] = None
    assignee_id: Optional[int] = None
    assignee_name: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class PaginatedTasks(BaseModel):
    items: List[TaskResponse]
    total: int
    page: int
    size: int
    pages: int
