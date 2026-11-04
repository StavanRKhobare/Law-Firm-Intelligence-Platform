"""API routes for legal matters, counsel assignment, and courts."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, or_, select
from datetime import date, datetime, time

from ..core.audit import record, set_actor
from ..core.permissions import (
    can_view_lawyer_matters, case_access, case_scope, require_case, sees_all_matters,
)
from ..core.security import get_current_active_user
from ..database import get_db
from ..models.models import (
    LegalCase, MatterType, StatuteSection, CaseLawyer, Lawyer,
    CaseClient, CaseOpposingParty, Location, Court, Client, OpposingParty,
    CaseNote, CaseStatusAudit, Evidence, Hearing, PincodeArea, Task,
)
from ..models.user import User
from ..schemas.legal_case import (
    LegalCaseCreate, LegalCaseUpdate, LegalCaseResponse, LegalCaseList,
    PaginatedLegalCases, AssignmentCreate, AssignmentResponse, CourtBrief,
    CasePermissions, CourtCreate, LocationCreate, LocationResponse, NoteCreate, NoteResponse, TimelineEvent,
    MATTER_STATUSES, OUTCOMES,
)
from .evidence import delete_stored_file

router = APIRouter()
courts_router = APIRouter()
locations_router = APIRouter()

ACTIVE = ("Filed", "Hearing", "Pending")


def lead_counsel_name(case: LegalCase) -> Optional[str]:
    for assignment in case.assignments:
        if assignment.role == "Lead Counsel" and assignment.end_date is None and assignment.lawyer:
            return f"{assignment.lawyer.fname} {assignment.lawyer.lname}"
    return None


def location_label(case: LegalCase) -> Optional[str]:
    if not case.location:
        return None
    label = case.location.landmark
    if case.location.pincode_area:
        label = f"{label}, {case.location.pincode_area.city}"
    return label


def require_ids(db: Session, column, ids, label: str) -> None:
    """404 naming the first id that does not exist. None values are ignored."""
    wanted = {i for i in ids if i is not None}
    if not wanted:
        return
    found = {row[0] for row in db.query(column).filter(column.in_(wanted)).all()}
    missing = sorted(wanted - found)
    if missing:
        raise HTTPException(status_code=404, detail=f"{label} {missing[0]} not found")


def replace_links(db: Session, model, case_id: int, column: str, values) -> None:
    """Make a matter's rows in a link table match the given values."""
    db.query(model).filter(model.case_id == case_id).delete(synchronize_session=False)
    for value in dict.fromkeys(values):
        db.add(model(case_id=case_id, **{column: value}))


def next_hearings(db: Session, case_ids) -> dict:
    if not case_ids:
        return {}
    rows = db.query(Hearing.case_id, func.min(Hearing.hearing_date)).filter(
        Hearing.case_id.in_(case_ids),
        Hearing.status == "Scheduled",
        Hearing.hearing_date >= date.today(),
    ).group_by(Hearing.case_id).all()
    return dict(rows)


def case_response(db: Session, case: LegalCase, user: User) -> LegalCaseResponse:
    response = LegalCaseResponse.model_validate(case)
    response.next_hearing = next_hearings(db, [case.case_id]).get(case.case_id)
    access = case_access(db, user, case.case_id)
    response.permissions = CasePermissions(**vars(access))
    return response


@router.post("/", response_model=LegalCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: LegalCaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Open a matter. A lawyer who opens one is put on it, as lead if no lead is named."""
    if user.role == "lawyer" and user.lawyer_id is None:
        raise HTTPException(status_code=403, detail="Your account is not linked to a lawyer record. Ask an admin to link it.")
    if db.query(LegalCase).filter(LegalCase.case_number == case_data.case_number).first():
        raise HTTPException(status_code=400, detail=f"Case number {case_data.case_number} already exists")

    assignments = list(case_data.assignments or [])
    leads = [a for a in assignments if a.role == "Lead Counsel" and a.end_date is None]
    if len(leads) > 1:
        raise HTTPException(status_code=400, detail="A matter can have only one active lead counsel")
    lawyer_ids = [a.lawyer_id for a in assignments]
    if len(lawyer_ids) != len(set(lawyer_ids)):
        raise HTTPException(status_code=400, detail="A lawyer can appear only once on a matter")
    if user.role != "admin" and any(a.role == "Lead Counsel" and a.lawyer_id != user.lawyer_id for a in leads):
        raise HTTPException(status_code=403, detail="Only an admin can name someone else as lead counsel")
    if user.role == "staff" and assignments:
        raise HTTPException(status_code=403, detail="Only an admin or a lawyer can assign counsel")
    if user.role == "lawyer" and user.lawyer_id not in lawyer_ids:
        assignments.append(AssignmentCreate(
            lawyer_id=user.lawyer_id,
            role="Associate" if leads else "Lead Counsel",
            assigned_date=max(date.today(), case_data.date_filed),
        ))
        lawyer_ids.append(user.lawyer_id)

    # Repeated values would collide on the composite keys, so keep each one once
    matter_types = list(dict.fromkeys(case_data.matter_types or []))
    statute_sections = list(dict.fromkeys(case_data.statute_sections or []))
    client_ids = list(dict.fromkeys(case_data.client_ids or []))
    party_ids = list(dict.fromkeys(case_data.party_ids or []))

    require_ids(db, Court.court_id, [case_data.court_id], "Court")
    require_ids(db, Location.location_id, [case_data.location_id], "Location")
    require_ids(db, Client.client_id, client_ids, "Client")
    require_ids(db, OpposingParty.party_id, party_ids, "Opposing party")
    require_ids(db, Lawyer.lawyer_id, lawyer_ids, "Lawyer")

    new_case = LegalCase(
        matter_title=case_data.matter_title,
        matter_description=case_data.matter_description,
        case_number=case_data.case_number,
        date_cause=case_data.date_cause,
        date_filed=case_data.date_filed,
        status=case_data.status,
        court_id=case_data.court_id,
        location_id=case_data.location_id,
        created_by=user.user_id,
    )
    if case_data.status == "Disposed":
        new_case.disposed_on = date.today()
    db.add(new_case)
    db.flush()

    for matter_type in matter_types:
        db.add(MatterType(case_id=new_case.case_id, matter_type=matter_type))
    for section in statute_sections:
        db.add(StatuteSection(case_id=new_case.case_id, statute_section=section))
    for client_id in client_ids:
        db.add(CaseClient(case_id=new_case.case_id, client_id=client_id))
    for party_id in party_ids:
        db.add(CaseOpposingParty(case_id=new_case.case_id, party_id=party_id))
    for assignment in assignments:
        db.add(CaseLawyer(
            case_id=new_case.case_id,
            lawyer_id=assignment.lawyer_id,
            role=assignment.role,
            assigned_date=assignment.assigned_date,
            end_date=assignment.end_date,
        ))

    record(db, user, "matter_created", "matter", new_case.case_id, new_case.case_id, {"case_number": new_case.case_number})
    db.commit()
    db.refresh(new_case)
    return case_response(db, new_case, user)


@router.get("/", response_model=PaginatedLegalCases)
async def get_cases(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    lawyer_id: Optional[int] = Query(None),
    court_id: Optional[int] = Query(None),
    matter_type: Optional[str] = Query(None),
    unassigned: bool = Query(False, description="Only matters with no active lead counsel"),
    scope: str = Query("all", pattern="^(all|mine)$", description="mine: only matters I can open"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """List matters. Rows the user may not open show only the title, number, status and lead."""
    query = db.query(LegalCase)
    if status:
        query = query.filter(LegalCase.status == status)
    if search:
        query = query.filter(or_(
            LegalCase.matter_title.ilike(f"%{search}%"),
            LegalCase.case_number.ilike(f"%{search}%"),
        ))
    if date_from:
        query = query.filter(LegalCase.date_filed >= date_from)
    if date_to:
        query = query.filter(LegalCase.date_filed <= date_to)
    if court_id:
        query = query.filter(LegalCase.court_id == court_id)
    if matter_type:
        query = query.filter(LegalCase.case_id.in_(
            select(MatterType.case_id).where(MatterType.matter_type == matter_type)
        ))
    if lawyer_id:
        if not can_view_lawyer_matters(user, lawyer_id):
            raise HTTPException(status_code=403, detail="You can only list your own matters")
        query = query.filter(LegalCase.case_id.in_(
            select(CaseLawyer.case_id).where(CaseLawyer.lawyer_id == lawyer_id, CaseLawyer.end_date.is_(None))
        ))
    if unassigned:
        query = query.filter(LegalCase.status != "Disposed", LegalCase.case_id.notin_(
            select(CaseLawyer.case_id).where(CaseLawyer.role == "Lead Counsel", CaseLawyer.end_date.is_(None))
        ))
    scope_clause = case_scope(user)
    if scope == "mine" and scope_clause is not None:
        query = query.filter(scope_clause)

    total = query.count()
    pages = (total + size - 1) // size
    cases = query.options(
        selectinload(LegalCase.assignments).joinedload(CaseLawyer.lawyer),
        selectinload(LegalCase.matter_types),
        joinedload(LegalCase.court),
        joinedload(LegalCase.location).joinedload(Location.pincode_area),
    ).order_by(LegalCase.date_filed.desc(), LegalCase.case_id.desc()).offset((page - 1) * size).limit(size).all()

    upcoming = next_hearings(db, [c.case_id for c in cases])
    if sees_all_matters(user):
        openable = {c.case_id for c in cases}
    elif user.lawyer_id:
        openable = {
            c.case_id for c in cases
            if any(a.lawyer_id == user.lawyer_id and a.end_date is None for a in c.assignments)
        }
    else:
        openable = set()

    items = []
    for case in cases:
        can_open = case.case_id in openable
        items.append(LegalCaseList(
            case_id=case.case_id,
            matter_title=case.matter_title,
            case_number=case.case_number,
            status=case.status,
            date_cause=case.date_cause,
            date_filed=case.date_filed,
            lead_counsel=lead_counsel_name(case),
            court_name=case.court.court_name if case.court and can_open else None,
            location_name=location_label(case) if can_open else None,
            matter_types=[m.matter_type for m in case.matter_types] if can_open else [],
            next_hearing=upcoming.get(case.case_id) if can_open else None,
            can_open=can_open,
        ))
    return PaginatedLegalCases(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/by-number/{case_number:path}", response_model=LegalCaseResponse)
async def get_case_by_number(
    case_number: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    case = db.query(LegalCase).filter(LegalCase.case_number == case_number).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case number {case_number} not found")
    return case_response(db, require_case(db, user, case.case_id), user)


@router.get("/{case_id}", response_model=LegalCaseResponse)
async def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    return case_response(db, require_case(db, user, case_id), user)


@router.put("/{case_id}", response_model=LegalCaseResponse)
async def update_case(
    case_id: int,
    case_data: LegalCaseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    case = require_case(db, user, case_id, "edit")
    changes = case_data.model_dump(exclude_unset=True)
    matter_types = changes.pop("matter_types", None)
    statute_sections = changes.pop("statute_sections", None)
    client_ids = changes.pop("client_ids", None)
    party_ids = changes.pop("party_ids", None)
    new_status = changes.pop("status", None)

    require_ids(db, Court.court_id, [changes.get("court_id")], "Court")
    require_ids(db, Location.location_id, [changes.get("location_id")], "Location")
    require_ids(db, Client.client_id, client_ids or [], "Client")
    require_ids(db, OpposingParty.party_id, party_ids or [], "Opposing party")
    number = changes.get("case_number")
    if number and db.query(LegalCase).filter(LegalCase.case_number == number, LegalCase.case_id != case_id).first():
        raise HTTPException(status_code=400, detail=f"Case number {number} already exists")
    # Check the dates as they will be stored, so changing only one of them is covered too
    date_cause = changes.get("date_cause", case.date_cause)
    date_filed = changes.get("date_filed", case.date_filed)
    if date_filed < date_cause:
        raise HTTPException(status_code=400, detail="Filing date cannot be before the cause of action")

    set_actor(db, user)
    for field, value in changes.items():
        setattr(case, field, value)
    if new_status:
        apply_status(db, case, new_status, None, None)
    if matter_types is not None:
        replace_links(db, MatterType, case_id, "matter_type", matter_types)
    if statute_sections is not None:
        replace_links(db, StatuteSection, case_id, "statute_section", statute_sections)
    if client_ids is not None:
        replace_links(db, CaseClient, case_id, "client_id", client_ids)
    if party_ids is not None:
        replace_links(db, CaseOpposingParty, case_id, "party_id", party_ids)
    record(db, user, "matter_updated", "matter", case_id, case_id, {"fields": sorted(case_data.model_fields_set)})
    db.commit()
    db.expire_all()
    return case_response(db, require_case(db, user, case_id), user)


def apply_status(db: Session, case: LegalCase, new_status: str, outcome: Optional[str], disposed_on: Optional[date]) -> None:
    if new_status == "Disposed":
        case.disposed_on = disposed_on or case.disposed_on or date.today()
        case.outcome = outcome or case.outcome
        # Nothing is listed on a closed matter any more
        for hearing in db.query(Hearing).filter(
            Hearing.case_id == case.case_id, Hearing.status == "Scheduled", Hearing.hearing_date >= date.today()
        ):
            hearing.status = "Cancelled"
            hearing.remarks = "Matter disposed"
    else:
        case.disposed_on = None
        case.outcome = None
    case.status = new_status


@router.patch("/{case_id}/status", response_model=LegalCaseResponse)
async def update_case_status(
    case_id: int,
    new_status: str = Query(..., description="Filed, Hearing, Pending or Disposed"),
    outcome: Optional[str] = Query(None, description="Won, Lost, Settled, Withdrawn, Dismissed or Other"),
    disposed_on: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Change a matter's status. Disposal records the outcome and cancels future hearings."""
    if new_status not in MATTER_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(MATTER_STATUSES)}")
    if outcome and outcome not in OUTCOMES:
        raise HTTPException(status_code=400, detail=f"Invalid outcome. Must be one of: {', '.join(OUTCOMES)}")
    case = require_case(db, user, case_id, "edit")
    if disposed_on and disposed_on < case.date_filed:
        raise HTTPException(status_code=400, detail="Disposal date cannot be before the filing date")
    previous = case.status
    set_actor(db, user)
    apply_status(db, case, new_status, outcome, disposed_on)
    record(db, user, "status_changed", "matter", case_id, case_id, {"from": previous, "to": new_status, "outcome": outcome})
    db.commit()
    db.refresh(case)
    return case_response(db, case, user)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    case = require_case(db, user, case_id, "delete")
    file_ids = [e.mongo_id for e in case.evidence if e.mongo_id]
    record(db, user, "matter_deleted", "matter", case_id, case_id, {"case_number": case.case_number, "title": case.matter_title})
    db.delete(case)
    db.commit()
    for file_id in file_ids:
        delete_stored_file(file_id)


@router.get("/{case_id}/lawyers", response_model=List[AssignmentResponse])
async def list_assignments(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    case = require_case(db, user, case_id)
    return case.assignments


@router.post("/{case_id}/lawyers", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def assign_lawyer(
    case_id: int,
    assignment: AssignmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Assign counsel. A new active lead ends the previous active lead."""
    require_case(db, user, case_id, "assign")
    lawyer = db.query(Lawyer).filter(Lawyer.lawyer_id == assignment.lawyer_id).first()
    if not lawyer:
        raise HTTPException(status_code=404, detail=f"Lawyer {assignment.lawyer_id} not found")
    if not lawyer.is_active:
        raise HTTPException(status_code=400, detail=f"{lawyer.fname} {lawyer.lname} is no longer active")

    if assignment.role == "Lead Counsel" and assignment.end_date is None:
        previous = db.query(CaseLawyer).filter(
            CaseLawyer.case_id == case_id,
            CaseLawyer.role == "Lead Counsel",
            CaseLawyer.end_date.is_(None),
            CaseLawyer.lawyer_id != assignment.lawyer_id,
        ).all()
        for row in previous:
            row.end_date = max(assignment.assigned_date, row.assigned_date)
        # The old lead must be closed before the new one is written (one_active_lead_per_case)
        db.flush()

    row = db.query(CaseLawyer).filter(
        CaseLawyer.case_id == case_id,
        CaseLawyer.lawyer_id == assignment.lawyer_id,
    ).first()
    if row:
        row.role = assignment.role
        row.assigned_date = assignment.assigned_date
        row.end_date = assignment.end_date
    else:
        row = CaseLawyer(
            case_id=case_id,
            lawyer_id=assignment.lawyer_id,
            role=assignment.role,
            assigned_date=assignment.assigned_date,
            end_date=assignment.end_date,
        )
        db.add(row)
    record(db, user, "counsel_assigned", "matter", case_id, case_id, {
        "lawyer": f"{lawyer.fname} {lawyer.lname}", "role": assignment.role,
    })
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{case_id}/lawyers/{lawyer_id}", response_model=AssignmentResponse)
async def end_assignment(
    case_id: int,
    lawyer_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Take a lawyer off a matter. The row stays, with an end date, as history."""
    require_case(db, user, case_id, "assign")
    row = db.query(CaseLawyer).filter(
        CaseLawyer.case_id == case_id,
        CaseLawyer.lawyer_id == lawyer_id,
        CaseLawyer.end_date.is_(None),
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="This lawyer is not active on this matter")
    row.end_date = max(date.today(), row.assigned_date)
    record(db, user, "counsel_removed", "matter", case_id, case_id, {"lawyer": row.lawyer_name})
    db.commit()
    db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Remarks and history
# ---------------------------------------------------------------------------

@router.get("/{case_id}/notes", response_model=List[NoteResponse])
async def list_notes(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    require_case(db, user, case_id)
    return db.query(CaseNote).filter(CaseNote.case_id == case_id).order_by(CaseNote.created_at.desc()).all()


@router.post("/{case_id}/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def add_note(
    case_id: int,
    data: NoteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    require_case(db, user, case_id, "work")
    note = CaseNote(case_id=case_id, body=data.body, author_id=user.user_id, author_name=user.full_name or user.username)
    db.add(note)
    db.flush()
    record(db, user, "note_added", "note", note.note_id, case_id)
    db.commit()
    db.refresh(note)
    return note


@router.delete("/{case_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    case_id: int,
    note_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    require_case(db, user, case_id)
    note = db.query(CaseNote).filter(CaseNote.note_id == note_id, CaseNote.case_id == case_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if user.role != "admin" and note.author_id != user.user_id:
        raise HTTPException(status_code=403, detail="Only the author or an admin can delete a note")
    record(db, user, "note_deleted", "note", note_id, case_id, {"body": note.body})
    db.delete(note)
    db.commit()


@router.get("/{case_id}/timeline", response_model=List[TimelineEvent])
async def get_timeline(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Everything that has happened on a matter, newest first, with listed hearings on top."""
    case = require_case(db, user, case_id)
    today = date.today()
    events = [TimelineEvent(at=at_midnight(case.date_filed), kind="filed", title=f"Matter filed as {case.case_number}")]

    for h in db.query(Hearing).filter(Hearing.case_id == case_id):
        upcoming = h.status == "Scheduled" and h.hearing_date >= today
        title = f"Hearing {h.status.lower()}" if h.status != "Scheduled" else "Hearing listed"
        if h.purpose:
            title += f": {h.purpose}"
        events.append(TimelineEvent(
            at=at_midnight(h.hearing_date), kind="hearing", title=title,
            detail=" | ".join(x for x in (h.outcome, h.remarks) if x) or None,
            actor=h.attending_lawyer and f"{h.attending_lawyer.fname} {h.attending_lawyer.lname}",
            upcoming=upcoming,
        ))
    for n in db.query(CaseNote).filter(CaseNote.case_id == case_id):
        events.append(TimelineEvent(at=n.created_at, kind="note", title="Remark added", detail=n.body, actor=n.author_name))
    for s in db.query(CaseStatusAudit).filter(CaseStatusAudit.case_id == case_id):
        events.append(TimelineEvent(
            at=s.changed_at, kind="status", title=f"Status changed from {s.old_status} to {s.new_status}", actor=s.changed_by,
        ))
    for e in db.query(Evidence).filter(Evidence.case_id == case_id):
        events.append(TimelineEvent(
            at=e.uploaded_at or at_midnight(e.filed_date), kind="document",
            title=f"{e.category} added", detail=e.description or e.file_name,
        ))
    for a in case.assignments:
        events.append(TimelineEvent(at=at_midnight(a.assigned_date), kind="counsel", title=f"{a.lawyer_name} assigned as {a.role}"))
        if a.end_date:
            events.append(TimelineEvent(at=at_midnight(a.end_date), kind="counsel", title=f"{a.lawyer_name} left the matter ({a.role})"))
    for t in db.query(Task).filter(Task.case_id == case_id, Task.status == "Done", Task.completed_at.isnot(None)):
        events.append(TimelineEvent(at=t.completed_at, kind="task", title=f"{t.kind} completed: {t.title}"))
    if case.status == "Disposed" and case.disposed_on:
        title = f"Matter disposed: {case.outcome}" if case.outcome else "Matter disposed"
        events.append(TimelineEvent(at=at_midnight(case.disposed_on), kind="disposed", title=title))

    upcoming = sorted((e for e in events if e.upcoming), key=lambda e: e.at)
    past = sorted((e for e in events if not e.upcoming), key=lambda e: e.at, reverse=True)
    return upcoming + past


def at_midnight(day: date) -> datetime:
    return datetime.combine(day, time.min)


@courts_router.get("/", response_model=List[CourtBrief])
async def list_courts(db: Session = Depends(get_db)):
    return db.query(Court).order_by(Court.court_name).all()


@courts_router.post("/", response_model=CourtBrief, status_code=status.HTTP_201_CREATED)
async def create_court(
    data: CourtCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    if data.pincode:
        upsert_pincode(db, data.pincode, data.city, data.district, data.state)
    court = Court(court_name=data.court_name, court_type=data.court_type, pincode=data.pincode or None)
    db.add(court)
    db.flush()
    record(db, user, "court_created", "court", court.court_id, detail={"name": court.court_name})
    db.commit()
    db.refresh(court)
    return court


def upsert_pincode(db: Session, pincode: str, city: Optional[str], district: Optional[str], state: Optional[str]) -> None:
    """A new pincode needs its city, district and state, because they are stored against it."""
    if db.get(PincodeArea, pincode):
        return
    if not (city and district and state):
        raise HTTPException(status_code=400, detail=f"Pincode {pincode} is new. Give its city, district and state.")
    db.add(PincodeArea(pincode=pincode, city=city, district=district, state=state))
    db.flush()


@locations_router.get("/", response_model=List[LocationResponse])
async def list_locations(db: Session = Depends(get_db)):
    rows = db.query(Location).options(joinedload(Location.pincode_area)).order_by(Location.landmark).all()
    return [
        LocationResponse(
            location_id=row.location_id,
            landmark=row.landmark,
            streetno=row.streetno,
            pincode=row.pincode,
            city=row.pincode_area.city if row.pincode_area else None,
        )
        for row in rows
    ]


@locations_router.post("/", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    data: LocationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    if data.pincode:
        upsert_pincode(db, data.pincode, data.city, data.district, data.state)
    location = Location(landmark=data.landmark, streetno=data.streetno, pincode=data.pincode or None)
    db.add(location)
    db.flush()
    record(db, user, "location_created", "location", location.location_id)
    db.commit()
    db.refresh(location)
    return LocationResponse(
        location_id=location.location_id, landmark=location.landmark, streetno=location.streetno,
        pincode=location.pincode, city=location.pincode_area.city if location.pincode_area else None,
    )
