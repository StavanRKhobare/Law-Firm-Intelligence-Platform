"""Hearings: the cause list and calendar, and the record of what happened at each listing."""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..core.audit import record, set_actor
from ..core.permissions import can_view_lawyer_matters, case_access, case_scope, require_case
from ..core.security import get_current_active_user
from ..database import get_db
from ..models.models import CaseLawyer, Court, Hearing, Lawyer, LegalCase
from ..models.user import User
from ..schemas.work import HearingCreate, HearingResponse, HearingResult, HearingUpdate
from .cases import lead_counsel_name

router = APIRouter()


def hearing_response(hearing: Hearing, can_work: bool = True) -> HearingResponse:
    case = hearing.legal_case
    court = hearing.court or case.court
    attending = hearing.attending_lawyer
    return HearingResponse(
        hearing_id=hearing.hearing_id,
        case_id=hearing.case_id,
        case_number=case.case_number,
        matter_title=case.matter_title,
        lead_counsel=lead_counsel_name(case),
        hearing_date=hearing.hearing_date,
        hearing_time=hearing.hearing_time,
        court_id=court.court_id if court else None,
        court_name=court.court_name if court else None,
        courtroom=hearing.courtroom,
        judge=hearing.judge,
        purpose=hearing.purpose,
        status=hearing.status,
        outcome=hearing.outcome,
        remarks=hearing.remarks,
        attended_by=hearing.attended_by,
        attended_by_name=f"{attending.fname} {attending.lname}" if attending else None,
        can_work=can_work,
    )


def check_references(db: Session, court_id: Optional[int], lawyer_id: Optional[int]) -> None:
    if court_id and not db.get(Court, court_id):
        raise HTTPException(status_code=404, detail=f"Court {court_id} not found")
    if lawyer_id and not db.get(Lawyer, lawyer_id):
        raise HTTPException(status_code=404, detail=f"Lawyer {lawyer_id} not found")


def get_hearing_or_404(db: Session, hearing_id: int) -> Hearing:
    hearing = db.get(Hearing, hearing_id)
    if not hearing:
        raise HTTPException(status_code=404, detail=f"Hearing {hearing_id} not found")
    return hearing


def list_query(db: Session):
    return db.query(Hearing).join(LegalCase, Hearing.case_id == LegalCase.case_id).options(
        joinedload(Hearing.court),
        joinedload(Hearing.attending_lawyer),
        joinedload(Hearing.legal_case).joinedload(LegalCase.court),
        joinedload(Hearing.legal_case).selectinload(LegalCase.assignments).joinedload(CaseLawyer.lawyer),
    )


@router.get("/", response_model=List[HearingResponse])
async def list_hearings(
    case_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    lawyer_id: Optional[int] = None,
    court_id: Optional[int] = None,
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Hearings the user may see. Ordered by date, ready for a cause list."""
    query = list_query(db)
    scope = case_scope(user)
    if scope is not None:
        query = query.filter(scope)
    if case_id:
        require_case(db, user, case_id)
        query = query.filter(Hearing.case_id == case_id)
    if date_from:
        query = query.filter(Hearing.hearing_date >= date_from)
    if date_to:
        query = query.filter(Hearing.hearing_date <= date_to)
    if status_filter:
        query = query.filter(Hearing.status == status_filter)
    if court_id:
        query = query.filter(Hearing.court_id == court_id)
    if lawyer_id:
        if not can_view_lawyer_matters(user, lawyer_id):
            raise HTTPException(status_code=403, detail="You can only list your own hearings")
        query = query.filter(Hearing.case_id.in_(
            select(CaseLawyer.case_id).where(CaseLawyer.lawyer_id == lawyer_id, CaseLawyer.end_date.is_(None))
        ))
    rows = query.order_by(Hearing.hearing_date, Hearing.hearing_time, Hearing.hearing_id).limit(limit).all()
    return [hearing_response(h) for h in rows]


@router.post("/", response_model=HearingResponse, status_code=status.HTTP_201_CREATED)
async def create_hearing(
    data: HearingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """List a hearing, or record one that already took place. A Filed matter moves to Hearing."""
    case = require_case(db, user, data.case_id, "work")
    check_references(db, data.court_id, data.attended_by)
    if case.status == "Disposed" and data.status == "Scheduled":
        raise HTTPException(status_code=409, detail="This matter is disposed. Reopen it to list a hearing.")
    fields = data.model_dump()
    fields["court_id"] = data.court_id or case.court_id
    hearing = Hearing(**fields, created_by=user.user_id)
    db.add(hearing)
    set_actor(db, user)
    if case.status == "Filed":
        case.status = "Hearing"
    db.flush()
    record(db, user, "hearing_added", "hearing", hearing.hearing_id, case.case_id, {"date": data.hearing_date})
    db.commit()
    db.refresh(hearing)
    return hearing_response(hearing)


@router.get("/{hearing_id}", response_model=HearingResponse)
async def get_hearing(
    hearing_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    hearing = get_hearing_or_404(db, hearing_id)
    require_case(db, user, hearing.case_id)
    return hearing_response(hearing)


@router.put("/{hearing_id}", response_model=HearingResponse)
async def update_hearing(
    hearing_id: int,
    data: HearingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    hearing = get_hearing_or_404(db, hearing_id)
    require_case(db, user, hearing.case_id, "work")
    changes = data.model_dump(exclude_unset=True)
    check_references(db, changes.get("court_id"), changes.get("attended_by"))
    for field, value in changes.items():
        setattr(hearing, field, value)
    record(db, user, "hearing_updated", "hearing", hearing_id, hearing.case_id, {"fields": sorted(changes)})
    db.commit()
    db.refresh(hearing)
    return hearing_response(hearing)


@router.post("/{hearing_id}/result", response_model=HearingResponse)
async def record_result(
    hearing_id: int,
    data: HearingResult,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Close a hearing with what happened. A next date lists the next hearing in one step."""
    hearing = get_hearing_or_404(db, hearing_id)
    case = require_case(db, user, hearing.case_id, "work")
    check_references(db, None, data.attended_by)
    if data.next_date and data.next_date <= hearing.hearing_date:
        raise HTTPException(status_code=400, detail="The next date must be after this hearing")
    if data.next_date and case.status == "Disposed":
        raise HTTPException(status_code=409, detail="This matter is disposed. Reopen it to list a hearing.")
    hearing.status = data.status
    hearing.outcome = data.outcome
    hearing.remarks = data.remarks
    if data.attended_by:
        hearing.attended_by = data.attended_by
    if data.next_date:
        db.add(Hearing(
            case_id=hearing.case_id,
            hearing_date=data.next_date,
            court_id=hearing.court_id,
            courtroom=hearing.courtroom,
            judge=hearing.judge,
            purpose=data.next_purpose,
            created_by=user.user_id,
        ))
    record(db, user, "hearing_result", "hearing", hearing_id, hearing.case_id, {"status": data.status, "next_date": data.next_date})
    db.commit()
    db.refresh(hearing)
    return hearing_response(hearing)


@router.delete("/{hearing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hearing(
    hearing_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """For entries made by mistake. To record that a hearing didn't happen, cancel it instead."""
    hearing = get_hearing_or_404(db, hearing_id)
    if not case_access(db, user, hearing.case_id).edit:
        raise HTTPException(status_code=403, detail="Only counsel on the matter or an admin can delete a hearing")
    record(db, user, "hearing_deleted", "hearing", hearing_id, hearing.case_id, {"date": hearing.hearing_date})
    db.delete(hearing)
    db.commit()
