"""Pydantic schemas for analytics."""
from typing import List, Optional
from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_cases: int
    filed_cases: int
    hearing_cases: int
    disposed_cases: int
    pending_cases: int
    total_lawyers: int
    total_clients: int
    total_opposing_parties: int
    total_evidence: int
    disposal_rate: float


class CasesByStatus(BaseModel):
    status: str
    count: int
    percentage: float


class CasesByMonth(BaseModel):
    month: str
    year: int
    total_cases: int
    active_cases: int
    disposed_cases: int


class MatterTypeStats(BaseModel):
    matter_type: str
    count: int
    percentage: float


class LocationCaseload(BaseModel):
    location_id: int
    landmark: Optional[str]
    city: Optional[str]
    matter_count: int
    matter_types: List[str]


class LawyerPerformance(BaseModel):
    lawyer_id: int
    lawyer_name: str
    designation: Optional[str]
    practice_group: Optional[str]
    total_cases: int
    active_cases: int
    disposed_cases: int
    disposal_rate: float
    evidence_filed: int


class PracticeGroupStats(BaseModel):
    group_id: int
    group_name: str
    total_lawyers: int
    total_cases: int
    active_cases: int
    disposed_cases: int
    disposal_rate: float


class TimeSeriesData(BaseModel):
    date: str
    count: int


class TrendAnalysis(BaseModel):
    period: str
    cases_trend: List[TimeSeriesData]
    total_change: int
    percentage_change: float


class RepeatPartyStats(BaseModel):
    party_id: int
    party_name: str
    total_cases: int
    active_cases: int
    disposed_cases: int
    repeat_party: bool
