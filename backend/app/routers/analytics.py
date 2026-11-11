"""Dashboard and reporting queries over the law-firm schema."""
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract, distinct
from datetime import date, datetime, timedelta
from collections import Counter, defaultdict

from ..database import get_db
from ..models.models import (
    LegalCase, Lawyer, Client, OpposingParty, Evidence,
    PracticeGroup, Location, PincodeArea, MatterType,
    CaseLawyer, CaseOpposingParty, CaseClient, Court, Hearing, JoinRequest, Task,
)
from ..models.user import User
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


@router.get("/firm")
async def firm_overview(db: Session = Depends(get_db)):
    """What a managing partner needs: risks, workload, how long matters take, how they end."""
    today = date.today()
    cases = db.query(LegalCase).options(
        joinedload(LegalCase.court),
        joinedload(LegalCase.matter_types),
        joinedload(LegalCase.assignments).joinedload(CaseLawyer.lawyer),
    ).all()
    cases = list({c.case_id: c for c in cases}.values())
    active = [c for c in cases if c.status != "Disposed"]
    hearings = db.query(Hearing).all()

    def lead(case):
        for a in case.assignments:
            if a.role == "Lead Counsel" and a.end_date is None:
                return a.lawyer_name
        return None

    def brief(case, **extra):
        return {
            "case_id": case.case_id, "case_number": case.case_number, "matter_title": case.matter_title,
            "status": case.status, "lead_counsel": lead(case), **extra,
        }

    scheduled_ahead = {h.case_id for h in hearings if h.status == "Scheduled" and h.hearing_date >= today}
    last_hearing = {}
    for h in hearings:
        if h.status != "Cancelled" and h.hearing_date <= today:
            last_hearing[h.case_id] = max(last_hearing.get(h.case_id, h.hearing_date), h.hearing_date)

    no_next_date = sorted(
        (c for c in active if c.case_id not in scheduled_ahead),
        key=lambda c: last_hearing.get(c.case_id, c.date_filed),
    )
    unassigned = [c for c in active if lead(c) is None]

    # How old open matters are
    buckets = {"Under 6 months": 0, "6 to 12 months": 0, "1 to 2 years": 0, "Over 2 years": 0}
    for c in active:
        age = (today - c.date_filed).days
        key = "Under 6 months" if age < 183 else "6 to 12 months" if age < 365 else "1 to 2 years" if age < 730 else "Over 2 years"
        buckets[key] += 1

    # How long matters take, and how they end
    durations, outcomes_by_type = defaultdict(list), defaultdict(Counter)
    outcomes = Counter()
    for c in cases:
        if c.status != "Disposed":
            continue
        if c.outcome:
            outcomes[c.outcome] += 1
        for m in c.matter_types:
            if c.disposed_on:
                durations[m.matter_type].append((c.disposed_on - c.date_filed).days)
            if c.outcome:
                outcomes_by_type[m.matter_type][c.outcome] += 1

    # Courts: load and how often listings are adjourned
    court_rows = {}
    for c in active:
        if c.court:
            court_rows.setdefault(c.court.court_id, {"court_name": c.court.court_name, "active_matters": 0, "hearings": 0, "adjourned": 0})
            court_rows[c.court.court_id]["active_matters"] += 1
    court_names = {c.court_id: c.court_name for c in db.query(Court)}
    for h in hearings:
        if h.status in ("Held", "Adjourned") and h.court_id:
            row = court_rows.setdefault(h.court_id, {"court_name": court_names.get(h.court_id), "active_matters": 0, "hearings": 0, "adjourned": 0})
            row["hearings"] += 1
            row["adjourned"] += h.status == "Adjourned"
    for row in court_rows.values():
        row["adjournment_rate"] = round(row["adjourned"] / row["hearings"] * 100) if row["hearings"] else None

    # Lawyers
    soon = today + timedelta(days=14)
    hearings_soon = Counter(h.case_id for h in hearings if h.status == "Scheduled" and today <= h.hearing_date <= soon)
    logins = {u.lawyer_id: u.user_id for u in db.query(User).filter(User.lawyer_id.isnot(None))}
    overdue_by_user = Counter(
        t.assignee_id for t in db.query(Task).filter(Task.status != "Done", Task.due_date < today) if t.assignee_id
    )
    lawyer_rows = []
    for lawyer in db.query(Lawyer).options(joinedload(Lawyer.practice_group)).filter(Lawyer.is_active.is_(True)):
        current = [a for a in lawyer.assignments if a.end_date is None and a.legal_case]
        open_rows = [a for a in current if a.legal_case.status != "Disposed"]
        lawyer_rows.append({
            "lawyer_id": lawyer.lawyer_id,
            "lawyer_name": f"{lawyer.fname} {lawyer.lname}",
            "designation": lawyer.designation,
            "practice_group": lawyer.practice_group.group_name if lawyer.practice_group else None,
            "active_matters": len(open_rows),
            "leading": sum(1 for a in open_rows if a.role == "Lead Counsel"),
            "hearings_next_14_days": sum(hearings_soon[a.case_id] for a in open_rows),
            "overdue_tasks": overdue_by_user[logins.get(lawyer.lawyer_id)],
        })
    lawyer_rows.sort(key=lambda r: r["active_matters"], reverse=True)

    # Filed against disposed, last 12 months
    months = []
    cursor = today.replace(day=1)
    for _ in range(12):
        months.append((cursor.year, cursor.month))
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    flow = {m: {"filed": 0, "disposed": 0} for m in months}
    for c in cases:
        key = (c.date_filed.year, c.date_filed.month)
        if key in flow:
            flow[key]["filed"] += 1
        if c.disposed_on and (c.disposed_on.year, c.disposed_on.month) in flow:
            flow[(c.disposed_on.year, c.disposed_on.month)]["disposed"] += 1

    open_tasks = db.query(Task).filter(Task.status != "Done").all()
    disposed_count = len(cases) - len(active)
    return {
        "headline": {
            "active_matters": len(active),
            "disposed_matters": disposed_count,
            "disposal_rate": round(disposed_count / len(cases) * 100, 1) if cases else 0,
            "hearings_next_7_days": sum(1 for h in hearings if h.status == "Scheduled" and today <= h.hearing_date <= today + timedelta(days=7)),
            "overdue_deadlines": sum(1 for t in open_tasks if t.kind != "Task" and t.due_date and t.due_date < today),
            "overdue_tasks": sum(1 for t in open_tasks if t.due_date and t.due_date < today),
            "unassigned_matters": len(unassigned),
            "matters_without_next_date": len(no_next_date),
            "pending_join_requests": db.query(JoinRequest).filter(JoinRequest.status == "Pending").count(),
        },
        "no_next_date": [
            brief(c, last_hearing=last_hearing.get(c.case_id)) for c in no_next_date[:20]
        ],
        "unassigned": [brief(c) for c in unassigned[:20]],
        "age_of_open_matters": [{"bucket": k, "count": v} for k, v in buckets.items()],
        "time_to_disposal": sorted(
            ({"matter_type": k, "matters": len(v), "average_days": round(sum(v) / len(v))} for k, v in durations.items()),
            key=lambda r: r["average_days"], reverse=True,
        ),
        "outcomes": [{"outcome": k, "count": v} for k, v in outcomes.most_common()],
        "outcomes_by_type": [
            {"matter_type": k, **{o: v.get(o, 0) for o in ("Won", "Lost", "Settled", "Withdrawn", "Dismissed", "Other")}}
            for k, v in outcomes_by_type.items()
        ],
        "courts": sorted(court_rows.values(), key=lambda r: r["active_matters"], reverse=True),
        "lawyers": lawyer_rows,
        "flow": [
            {"label": datetime(y, m, 1).strftime("%b %y"), **flow[(y, m)]} for y, m in reversed(months)
        ],
    }
