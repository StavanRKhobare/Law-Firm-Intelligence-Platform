"""Dashboard and reporting queries over the law-firm schema."""
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract, distinct
from datetime import datetime, timedelta
from collections import defaultdict

from ..database import get_db
from ..models.models import (
    LegalCase, Lawyer, Client, OpposingParty, Evidence,
    PracticeGroup, Location, PincodeArea, MatterType,
    CaseLawyer, CaseOpposingParty, CaseClient,
)
from ..schemas.analytics import (
    DashboardStats, CasesByStatus, CasesByMonth, MatterTypeStats,
    LocationCaseload, LawyerPerformance, PracticeGroupStats,
    TrendAnalysis, TimeSeriesData, RepeatPartyStats,
)

router = APIRouter()
ACTIVE = ("Filed", "Hearing", "Pending")


def _count(db, model, pk, *filters):
    query = db.query(func.count(pk))
    for clause in filters:
        query = query.filter(clause)
    return query.scalar() or 0


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    total = _count(db, LegalCase, LegalCase.case_id)
    filed = _count(db, LegalCase, LegalCase.case_id, LegalCase.status == "Filed")
    hearing = _count(db, LegalCase, LegalCase.case_id, LegalCase.status == "Hearing")
    disposed = _count(db, LegalCase, LegalCase.case_id, LegalCase.status == "Disposed")
    pending = _count(db, LegalCase, LegalCase.case_id, LegalCase.status == "Pending")
    disposal_rate = (disposed / total * 100) if total else 0
    return DashboardStats(
        total_cases=total,
        filed_cases=filed,
        hearing_cases=hearing,
        disposed_cases=disposed,
        pending_cases=pending,
        total_lawyers=_count(db, Lawyer, Lawyer.lawyer_id),
        total_clients=_count(db, Client, Client.client_id),
        total_opposing_parties=_count(db, OpposingParty, OpposingParty.party_id),
        total_evidence=_count(db, Evidence, Evidence.evidence_id),
        disposal_rate=round(disposal_rate, 2),
    )


@router.get("/cases/by-status", response_model=List[CasesByStatus])
async def get_cases_by_status(db: Session = Depends(get_db)):
    total = _count(db, LegalCase, LegalCase.case_id)
    if total == 0:
        return []
    rows = db.query(LegalCase.status, func.count(LegalCase.case_id)).group_by(LegalCase.status).all()
    return [
        CasesByStatus(status=status, count=count, percentage=round(count / total * 100, 2))
        for status, count in rows
    ]


@router.get("/cases/by-month", response_model=List[CasesByMonth])
async def get_cases_by_month(months: int = Query(12, ge=1, le=24), db: Session = Depends(get_db)):
    rows = db.query(
        extract("year", LegalCase.date_filed),
        extract("month", LegalCase.date_filed),
        LegalCase.status,
    ).all()
    monthly = defaultdict(lambda: {"total": 0, "active": 0, "disposed": 0})
    for year, month, status in rows:
        key = f"{int(year)}-{int(month):02d}"
        monthly[key]["total"] += 1
        if status in ACTIVE:
            monthly[key]["active"] += 1
        elif status == "Disposed":
            monthly[key]["disposed"] += 1
    result = []
    for key in sorted(monthly.keys(), reverse=True)[:months]:
        year, month = key.split("-")
        result.append(CasesByMonth(
            month=datetime(int(year), int(month), 1).strftime("%B"),
            year=int(year),
            total_cases=monthly[key]["total"],
            active_cases=monthly[key]["active"],
            disposed_cases=monthly[key]["disposed"],
        ))
    return list(reversed(result))


@router.get("/cases/by-matter-type", response_model=List[MatterTypeStats])
async def get_cases_by_matter_type(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    total = db.query(func.count(distinct(MatterType.case_id))).scalar() or 0
    if total == 0:
        return []
    rows = db.query(
        MatterType.matter_type,
        func.count(MatterType.case_id),
    ).group_by(MatterType.matter_type).order_by(func.count(MatterType.case_id).desc()).limit(limit).all()
    return [
        MatterTypeStats(matter_type=name, count=count, percentage=round(count / total * 100, 2))
        for name, count in rows
    ]


@router.get("/cases/trend", response_model=TrendAnalysis)
async def get_case_trend(
    period: str = Query("monthly"),
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
):
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    rows = db.query(LegalCase.date_filed).filter(
        LegalCase.date_filed >= start_date,
        LegalCase.date_filed <= end_date,
    ).all()
    counts = defaultdict(int)
    for (filed,) in rows:
        counts[str(filed)] += 1
    series = []
    current = start_date
    while current <= end_date:
        series.append(TimeSeriesData(date=str(current), count=counts.get(str(current), 0)))
        current += timedelta(days=1)
    first_half = sum(point.count for point in series[:len(series) // 2])
    second_half = sum(point.count for point in series[len(series) // 2:])
    change = ((second_half - first_half) / first_half * 100) if first_half else 0
    return TrendAnalysis(
        period=period,
        cases_trend=series,
        total_change=second_half - first_half,
        percentage_change=round(change, 2),
    )


@router.get("/locations/caseload", response_model=List[LocationCaseload])
async def get_location_caseload(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    rows = db.query(
        Location.location_id,
        Location.landmark,
        PincodeArea.city,
        func.count(LegalCase.case_id),
    ).join(LegalCase).outerjoin(
        PincodeArea, Location.pincode == PincodeArea.pincode
    ).group_by(Location.location_id, Location.landmark, PincodeArea.city).order_by(
        func.count(LegalCase.case_id).desc()
    ).limit(limit).all()

    result = []
    for location_id, landmark, city, matter_count in rows:
        types = db.query(distinct(MatterType.matter_type)).join(LegalCase).filter(
            LegalCase.location_id == location_id
        ).all()
        result.append(LocationCaseload(
            location_id=location_id,
            landmark=landmark,
            city=city,
            matter_count=matter_count,
            matter_types=[row[0] for row in types],
        ))
    return result


@router.get("/lawyers/performance", response_model=List[LawyerPerformance])
async def get_lawyer_performance(
    limit: int = Query(20, ge=1, le=100),
    order_by: str = Query("cases"),
    db: Session = Depends(get_db),
):
    lawyers = db.query(Lawyer).options(joinedload(Lawyer.practice_group)).all()
    performance = []
    for lawyer in lawyers:
        cases = db.query(LegalCase).join(CaseLawyer).filter(
            CaseLawyer.lawyer_id == lawyer.lawyer_id,
            CaseLawyer.end_date.is_(None),
        ).all()
        total = len(cases)
        if total == 0:
            continue
        disposed = sum(1 for case in cases if case.status == "Disposed")
        evidence_count = db.query(func.count(Evidence.evidence_id)).filter(
            Evidence.lawyer_id == lawyer.lawyer_id
        ).scalar() or 0
        performance.append(LawyerPerformance(
            lawyer_id=lawyer.lawyer_id,
            lawyer_name=f"{lawyer.fname} {lawyer.lname}",
            designation=lawyer.designation,
            practice_group=lawyer.practice_group.group_name if lawyer.practice_group else None,
            total_cases=total,
            active_cases=sum(1 for case in cases if case.status in ACTIVE),
            disposed_cases=disposed,
            disposal_rate=round(disposed / total * 100, 2),
            evidence_filed=evidence_count,
        ))
    if order_by == "disposal_rate":
        performance.sort(key=lambda row: row.disposal_rate, reverse=True)
    else:
        performance.sort(key=lambda row: row.total_cases, reverse=True)
    return performance[:limit]


@router.get("/practice-groups/statistics", response_model=List[PracticeGroupStats])
async def get_practice_group_statistics(db: Session = Depends(get_db)):
    result = []
    for group in db.query(PracticeGroup).all():
        lawyer_count = db.query(func.count(Lawyer.lawyer_id)).filter(Lawyer.group_id == group.group_id).scalar() or 0
        cases = db.query(LegalCase).join(CaseLawyer).join(Lawyer).filter(
            Lawyer.group_id == group.group_id,
            CaseLawyer.end_date.is_(None),
        ).distinct().all()
        total = len(cases)
        disposed = sum(1 for case in cases if case.status == "Disposed")
        result.append(PracticeGroupStats(
            group_id=group.group_id,
            group_name=group.group_name,
            total_lawyers=lawyer_count,
            total_cases=total,
            active_cases=sum(1 for case in cases if case.status in ACTIVE),
            disposed_cases=disposed,
            disposal_rate=round(disposed / total * 100, 2) if total else 0,
        ))
    return result


@router.get("/opposing-parties/repeat", response_model=List[RepeatPartyStats])
async def get_repeat_parties(
    min_cases: int = Query(2, ge=2),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    rows = db.query(
        OpposingParty,
        func.count(CaseOpposingParty.case_id),
    ).outerjoin(CaseOpposingParty).group_by(OpposingParty.party_id).having(
        func.count(CaseOpposingParty.case_id) >= min_cases
    ).order_by(func.count(CaseOpposingParty.case_id).desc()).limit(limit).all()

    result = []
    for party, case_count in rows:
        cases = db.query(LegalCase).join(CaseOpposingParty).filter(
            CaseOpposingParty.party_id == party.party_id
        ).all()
        result.append(RepeatPartyStats(
            party_id=party.party_id,
            party_name=f"{party.fname} {party.lname}",
            total_cases=case_count,
            active_cases=sum(1 for case in cases if case.status in ACTIVE),
            disposed_cases=sum(1 for case in cases if case.status == "Disposed"),
            repeat_party=bool(party.repeat_party),
        ))
    return result


@router.get("/clients/statistics")
async def get_client_statistics(db: Session = Depends(get_db)):
    total = _count(db, Client, Client.client_id)
    with_notes = db.query(func.count(Client.client_id)).filter(
        Client.notes.isnot(None), Client.notes != ""
    ).scalar() or 0
    repeat_clients = db.query(func.count(Client.client_id)).select_from(Client).join(CaseClient).group_by(
        Client.client_id
    ).having(func.count(CaseClient.case_id) > 1).count()
    return {
        "total_clients": total,
        "clients_with_notes": with_notes,
        "repeat_clients": repeat_clients,
    }


@router.get("/evidence/statistics")
async def get_evidence_statistics(db: Session = Depends(get_db)):
    total = _count(db, Evidence, Evidence.evidence_id)
    with_files = db.query(func.count(Evidence.evidence_id)).filter(Evidence.mongo_id.isnot(None)).scalar() or 0
    distribution = {}
    for label in ("Received", "Under Review", "Filed", "Produced"):
        distribution[label] = db.query(func.count(Evidence.evidence_id)).filter(Evidence.status == label).scalar() or 0
    cases_with_evidence = db.query(func.count(distinct(Evidence.case_id))).scalar() or 0
    return {
        "total_evidence": total,
        "with_files": with_files,
        "without_files": total - with_files,
        "status_distribution": distribution,
        "cases_with_evidence": cases_with_evidence,
    }
