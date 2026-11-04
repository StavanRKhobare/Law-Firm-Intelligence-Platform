"""API routes for legal matters, counsel assignment, and courts."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import or_
from datetime import date

from ..database import get_db
from ..models.models import (
    LegalCase, MatterType, StatuteSection, CaseLawyer, Lawyer,
    CaseClient, CaseOpposingParty, Location, Court, Client, OpposingParty,
)
from ..schemas.legal_case import (
    LegalCaseCreate, LegalCaseUpdate, LegalCaseResponse, LegalCaseList,
    PaginatedLegalCases, AssignmentCreate, AssignmentResponse, CourtBrief,
    MATTER_STATUSES,
)

router = APIRouter()
courts_router = APIRouter()

ACTIVE = ("Filed", "Hearing", "Pending")


def get_case_or_404(db: Session, case_id: int) -> LegalCase:
    case = db.query(LegalCase).filter(LegalCase.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Matter {case_id} not found")
    return case


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


@router.post("/", response_model=LegalCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(case_data: LegalCaseCreate, db: Session = Depends(get_db)):
    """Create a matter, its classifications, parties, and counsel assignments."""
    if db.query(LegalCase).filter(LegalCase.case_number == case_data.case_number).first():
        raise HTTPException(status_code=400, detail=f"Case number {case_data.case_number} already exists")

    assignments = case_data.assignments or []
    leads = [a for a in assignments if a.role == "Lead Counsel" and a.end_date is None]
    if len(leads) > 1:
        raise HTTPException(status_code=400, detail="A matter can have only one active lead counsel")
    lawyer_ids = [a.lawyer_id for a in assignments]
    if len(lawyer_ids) != len(set(lawyer_ids)):
        raise HTTPException(status_code=400, detail="A lawyer can appear only once on a matter")

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
    )
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

    db.commit()
    db.refresh(new_case)
    return new_case


@router.get("/", response_model=PaginatedLegalCases)
async def get_cases(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    lawyer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """List matters. lawyer_id matches any active assignment, not a single foreign key."""
    query = db.query(LegalCase)
    if status:
        query = query.filter(LegalCase.status == status)
    if search:
        query = query.filter(or_(
            LegalCase.matter_title.ilike(f"%{search}%"),
            LegalCase.case_number.ilike(f"%{search}%"),
        ))
    if date_from:
        query = query.filter(LegalCase.date_cause >= date_from)
    if date_to:
        query = query.filter(LegalCase.date_cause <= date_to)
    if lawyer_id:
        query = query.join(CaseLawyer).filter(
            CaseLawyer.lawyer_id == lawyer_id,
            CaseLawyer.end_date.is_(None),
        )

    total = query.count()
    pages = (total + size - 1) // size
    cases = query.options(
        selectinload(LegalCase.assignments).joinedload(CaseLawyer.lawyer),
        joinedload(LegalCase.court),
        joinedload(LegalCase.location).joinedload(Location.pincode_area),
    ).offset((page - 1) * size).limit(size).all()

    items = [
        LegalCaseList(
            case_id=case.case_id,
            matter_title=case.matter_title,
            case_number=case.case_number,
            status=case.status,
            date_cause=case.date_cause,
            lead_counsel=lead_counsel_name(case),
            court_name=case.court.court_name if case.court else None,
            location_name=location_label(case),
        )
        for case in cases
    ]
    return PaginatedLegalCases(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/by-number/{case_number:path}", response_model=LegalCaseResponse)
async def get_case_by_number(case_number: str, db: Session = Depends(get_db)):
    case = db.query(LegalCase).options(
        joinedload(LegalCase.court),
        joinedload(LegalCase.location),
        joinedload(LegalCase.matter_types),
        joinedload(LegalCase.statute_sections),
        joinedload(LegalCase.clients),
        joinedload(LegalCase.opposing_parties),
    ).filter(LegalCase.case_number == case_number).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case number {case_number} not found")
    return case


@router.get("/{case_id}", response_model=LegalCaseResponse)
async def get_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(LegalCase).options(
        joinedload(LegalCase.court),
        joinedload(LegalCase.location).joinedload(Location.pincode_area),
        joinedload(LegalCase.matter_types),
        joinedload(LegalCase.statute_sections),
        joinedload(LegalCase.clients),
        joinedload(LegalCase.opposing_parties),
        joinedload(LegalCase.evidence),
    ).filter(LegalCase.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Matter {case_id} not found")
    return case


@router.put("/{case_id}", response_model=LegalCaseResponse)
async def update_case(case_id: int, case_data: LegalCaseUpdate, db: Session = Depends(get_db)):
    case = get_case_or_404(db, case_id)
    changes = case_data.model_dump(exclude_unset=True)
    require_ids(db, Court.court_id, [changes.get("court_id")], "Court")
    require_ids(db, Location.location_id, [changes.get("location_id")], "Location")
    # Check the dates as they will be stored, so changing only one of them is covered too
    date_cause = changes.get("date_cause", case.date_cause)
    date_filed = changes.get("date_filed", case.date_filed)
    if date_filed < date_cause:
        raise HTTPException(status_code=400, detail="Filing date cannot be before the cause of action")
    for field, value in changes.items():
        setattr(case, field, value)
    db.commit()
    db.refresh(case)
    return case


@router.patch("/{case_id}/status", response_model=LegalCaseResponse)
async def update_case_status(
    case_id: int,
    new_status: str = Query(..., description="Filed, Hearing, Pending or Disposed"),
    db: Session = Depends(get_db),
):
    """Change only the status of a matter (what the desktop app's updateStatus call uses)."""
    if new_status not in MATTER_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(MATTER_STATUSES)}")
    case = get_case_or_404(db, case_id)
    case.status = new_status
    db.commit()
    db.refresh(case)
    return case


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(case_id: int, db: Session = Depends(get_db)):
    case = get_case_or_404(db, case_id)
    db.delete(case)
    db.commit()


@router.get("/{case_id}/lawyers", response_model=List[AssignmentResponse])
async def list_assignments(case_id: int, db: Session = Depends(get_db)):
    get_case_or_404(db, case_id)
    rows = db.query(CaseLawyer).options(joinedload(CaseLawyer.lawyer)).filter(
        CaseLawyer.case_id == case_id
    ).all()
    return [
        AssignmentResponse(
            lawyer_id=row.lawyer_id,
            role=row.role,
            assigned_date=row.assigned_date,
            end_date=row.end_date,
            lawyer_name=f"{row.lawyer.fname} {row.lawyer.lname}" if row.lawyer else None,
        )
        for row in rows
    ]


@router.post("/{case_id}/lawyers", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def assign_lawyer(case_id: int, assignment: AssignmentCreate, db: Session = Depends(get_db)):
    """Assign counsel. A new active lead ends the previous active lead."""
    get_case_or_404(db, case_id)
    lawyer = db.query(Lawyer).filter(Lawyer.lawyer_id == assignment.lawyer_id).first()
    if not lawyer:
        raise HTTPException(status_code=404, detail=f"Lawyer {assignment.lawyer_id} not found")

    if assignment.role == "Lead Counsel" and assignment.end_date is None:
        previous = db.query(CaseLawyer).filter(
            CaseLawyer.case_id == case_id,
            CaseLawyer.role == "Lead Counsel",
            CaseLawyer.end_date.is_(None),
            CaseLawyer.lawyer_id != assignment.lawyer_id,
        ).all()
        for row in previous:
            row.end_date = assignment.assigned_date if assignment.assigned_date >= row.assigned_date else row.assigned_date

    existing = db.query(CaseLawyer).filter(
        CaseLawyer.case_id == case_id,
        CaseLawyer.lawyer_id == assignment.lawyer_id,
    ).first()
    if existing:
        existing.role = assignment.role
        existing.assigned_date = assignment.assigned_date
        existing.end_date = assignment.end_date
        row = existing
    else:
        row = CaseLawyer(
            case_id=case_id,
            lawyer_id=assignment.lawyer_id,
            role=assignment.role,
            assigned_date=assignment.assigned_date,
            end_date=assignment.end_date,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return AssignmentResponse(
        lawyer_id=row.lawyer_id,
        role=row.role,
        assigned_date=row.assigned_date,
        end_date=row.end_date,
        lawyer_name=f"{lawyer.fname} {lawyer.lname}",
    )


@courts_router.get("/", response_model=List[CourtBrief])
async def list_courts(db: Session = Depends(get_db)):
    return db.query(Court).order_by(Court.court_name).all()
