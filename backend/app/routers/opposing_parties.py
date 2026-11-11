"""API routes for opposing parties. Lawyers see names firm-wide, for conflict checks, and details on their own matters."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from ..core.audit import record
from ..core.permissions import sees_all_matters, visible_party_ids
from ..core.security import get_current_active_user, require_role
from ..database import get_db
from ..models.models import OpposingParty, OpposingPartyPhoneNo, CaseOpposingParty
from ..models.user import User
from ..schemas.opposing_party import (
    PartyCreate, PartyUpdate, PartyResponse, PartyDetailed,
    PartyList, PaginatedParties, CaseBrief,
)

router = APIRouter()
ACTIVE = ("Filed", "Hearing", "Pending")


def get_party_or_404(db: Session, party_id: int) -> OpposingParty:
    party = db.query(OpposingParty).filter(OpposingParty.party_id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail=f"Opposing party {party_id} not found")
    return party


def can_open(db: Session, user: User, party_id: int) -> bool:
    visible = visible_party_ids(user)
    if visible is None:
        return True
    return db.query(OpposingParty.party_id).filter(OpposingParty.party_id == party_id, OpposingParty.party_id.in_(visible)).first() is not None


def require_party(db: Session, user: User, party_id: int) -> OpposingParty:
    party = get_party_or_404(db, party_id)
    if not can_open(db, user, party_id):
        raise HTTPException(status_code=403, detail="This opposing party is not on any of your matters")
    return party


@router.post("/", response_model=PartyResponse, status_code=status.HTTP_201_CREATED)
async def create_party(
    data: PartyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    payload = data.model_dump(exclude={"phone_numbers"})
    party = OpposingParty(**payload)
    db.add(party)
    db.flush()
    # dict.fromkeys drops repeats; (party_id, phoneno) is the table's primary key
    for number in dict.fromkeys(data.phone_numbers or []):
        db.add(OpposingPartyPhoneNo(party_id=party.party_id, phoneno=number))
    record(db, user, "party_created", "party", party.party_id)
    db.commit()
    db.refresh(party)
    return party


@router.get("/", response_model=PaginatedParties)
async def get_parties(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    scope: str = Query("all", pattern="^(all|mine)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    query = db.query(OpposingParty)
    visible = visible_party_ids(user)
    if scope == "mine" and visible is not None:
        query = query.filter(OpposingParty.party_id.in_(visible))
    if search:
        query = query.filter(or_(
            OpposingParty.fname.ilike(f"%{search}%"),
            OpposingParty.lname.ilike(f"%{search}%"),
            OpposingParty.email.ilike(f"%{search}%"),
        ))
    total = query.count()
    pages = (total + size - 1) // size
    parties = query.order_by(OpposingParty.fname, OpposingParty.lname).offset((page - 1) * size).limit(size).all()
    openable = None if visible is None else {
        row[0] for row in db.query(OpposingParty.party_id).filter(OpposingParty.party_id.in_(visible))
    }
    items = []
    for party in parties:
        total_cases = db.query(func.count(CaseOpposingParty.case_id)).filter(
            CaseOpposingParty.party_id == party.party_id
        ).scalar() or 0
        allowed = openable is None or party.party_id in openable
        items.append(PartyList(
            party_id=party.party_id,
            fname=party.fname,
            lname=party.lname,
            email=party.email if allowed else None,
            repeat_party=party.repeat_party,
            total_cases=total_cases,
            can_open=allowed,
        ))
    return PaginatedParties(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{party_id}", response_model=PartyDetailed)
async def get_party(
    party_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    party = require_party(db, user, party_id)
    cases = sorted(party.cases, key=lambda c: c.date_cause, reverse=True)
    return PartyDetailed(
        party_id=party.party_id,
        fname=party.fname,
        lname=party.lname,
        email=party.email,
        address=party.address,
        sex=party.sex,
        repeat_party=party.repeat_party,
        phone_numbers=[p.phoneno for p in party.phone_numbers],
        total_cases=len(cases),
        active_cases=sum(1 for c in cases if c.status in ACTIVE),
        disposed_cases=sum(1 for c in cases if c.status == "Disposed"),
        recent_cases=[
            CaseBrief(case_id=c.case_id, matter_title=c.matter_title, case_number=c.case_number, status=c.status)
            for c in cases
        ],
    )


@router.put("/{party_id}", response_model=PartyResponse)
async def update_party(
    party_id: int,
    data: PartyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    party = require_party(db, user, party_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(party, field, value)
    record(db, user, "party_updated", "party", party_id)
    db.commit()
    db.refresh(party)
    return party


@router.delete("/{party_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_party(
    party_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(["admin"])),
):
    party = get_party_or_404(db, party_id)
    if party.cases:
        raise HTTPException(status_code=409, detail="This opposing party is on a matter. Remove them from it first.")
    record(db, admin, "party_deleted", "party", party_id, detail={"name": f"{party.fname} {party.lname}"})
    db.delete(party)
    db.commit()


@router.post("/{party_id}/phones", status_code=status.HTTP_201_CREATED)
async def add_phone(
    party_id: int,
    phoneno: str = Query(..., max_length=15),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    require_party(db, user, party_id)
    if db.query(OpposingPartyPhoneNo).filter(OpposingPartyPhoneNo.party_id == party_id, OpposingPartyPhoneNo.phoneno == phoneno).first():
        raise HTTPException(status_code=400, detail="Phone number already recorded for this party")
    db.add(OpposingPartyPhoneNo(party_id=party_id, phoneno=phoneno))
    db.commit()
    return {"party_id": party_id, "phoneno": phoneno}


@router.delete("/{party_id}/phones/{phoneno}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_phone(
    party_id: int,
    phoneno: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    require_party(db, user, party_id)
    row = db.query(OpposingPartyPhoneNo).filter(
        OpposingPartyPhoneNo.party_id == party_id,
        OpposingPartyPhoneNo.phoneno == phoneno,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Phone number not found")
    db.delete(row)
    db.commit()


@router.get("/{party_id}/cases", response_model=List[CaseBrief])
async def get_party_cases(
    party_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    party = require_party(db, user, party_id)
    return [
        CaseBrief(case_id=c.case_id, matter_title=c.matter_title, case_number=c.case_number, status=c.status)
        for c in sorted(party.cases, key=lambda c: c.date_cause, reverse=True)
    ]
