"""API routes for opposing parties."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from ..database import get_db
from ..models.models import OpposingParty, OpposingPartyPhoneNo, CaseOpposingParty
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


@router.post("/", response_model=PartyResponse, status_code=status.HTTP_201_CREATED)
async def create_party(data: PartyCreate, db: Session = Depends(get_db)):
    payload = data.model_dump(exclude={"phone_numbers"})
    party = OpposingParty(**payload)
    db.add(party)
    db.flush()
    # dict.fromkeys drops repeats; (party_id, phoneno) is the table's primary key
    for number in dict.fromkeys(data.phone_numbers or []):
        db.add(OpposingPartyPhoneNo(party_id=party.party_id, phoneno=number))
    db.commit()
    db.refresh(party)
    return party


@router.get("/", response_model=PaginatedParties)
async def get_parties(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    repeat_party: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    query = db.query(OpposingParty)
    if search:
        query = query.filter(or_(
            OpposingParty.fname.ilike(f"%{search}%"),
            OpposingParty.lname.ilike(f"%{search}%"),
            OpposingParty.email.ilike(f"%{search}%"),
        ))
    if repeat_party is not None:
        query = query.filter(OpposingParty.repeat_party == repeat_party)
    total = query.count()
    pages = (total + size - 1) // size
    parties = query.offset((page - 1) * size).limit(size).all()
    items = []
    for party in parties:
        total_cases = db.query(func.count(CaseOpposingParty.case_id)).filter(
            CaseOpposingParty.party_id == party.party_id
        ).scalar() or 0
        items.append(PartyList(
            party_id=party.party_id,
            fname=party.fname,
            lname=party.lname,
            email=party.email,
            repeat_party=bool(party.repeat_party),
            total_cases=total_cases,
        ))
    return PaginatedParties(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{party_id}", response_model=PartyDetailed)
async def get_party(party_id: int, db: Session = Depends(get_db)):
    party = get_party_or_404(db, party_id)
    cases = sorted(party.cases, key=lambda c: c.date_cause, reverse=True)
    return PartyDetailed(
        party_id=party.party_id,
        fname=party.fname,
        lname=party.lname,
        email=party.email,
        address=party.address,
        sex=party.sex,
        repeat_party=bool(party.repeat_party),
        phone_numbers=[p.phoneno for p in party.phone_numbers],
        total_cases=len(cases),
        active_cases=sum(1 for c in cases if c.status in ACTIVE),
        disposed_cases=sum(1 for c in cases if c.status == "Disposed"),
        recent_cases=[
            CaseBrief(case_id=c.case_id, matter_title=c.matter_title, case_number=c.case_number, status=c.status)
            for c in cases[:5]
        ],
    )


@router.put("/{party_id}", response_model=PartyResponse)
async def update_party(party_id: int, data: PartyUpdate, db: Session = Depends(get_db)):
    party = get_party_or_404(db, party_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(party, field, value)
    db.commit()
    db.refresh(party)
    return party


@router.delete("/{party_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_party(party_id: int, db: Session = Depends(get_db)):
    party = get_party_or_404(db, party_id)
    db.delete(party)
    db.commit()


@router.post("/{party_id}/phones", status_code=status.HTTP_201_CREATED)
async def add_phone(party_id: int, phoneno: str = Query(...), db: Session = Depends(get_db)):
    get_party_or_404(db, party_id)
    if db.query(OpposingPartyPhoneNo).filter(OpposingPartyPhoneNo.party_id == party_id, OpposingPartyPhoneNo.phoneno == phoneno).first():
        raise HTTPException(status_code=400, detail="Phone number already recorded for this opposing party")
    db.add(OpposingPartyPhoneNo(party_id=party_id, phoneno=phoneno))
    db.commit()
    return {"party_id": party_id, "phoneno": phoneno}


@router.delete("/{party_id}/phones/{phoneno}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_phone(party_id: int, phoneno: str, db: Session = Depends(get_db)):
    row = db.query(OpposingPartyPhoneNo).filter(
        OpposingPartyPhoneNo.party_id == party_id,
        OpposingPartyPhoneNo.phoneno == phoneno,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Phone number not found")
    db.delete(row)
    db.commit()


@router.get("/{party_id}/cases", response_model=List[CaseBrief])
async def get_party_cases(party_id: int, db: Session = Depends(get_db)):
    party = get_party_or_404(db, party_id)
    return [
        CaseBrief(case_id=c.case_id, matter_title=c.matter_title, case_number=c.case_number, status=c.status)
        for c in sorted(party.cases, key=lambda c: c.date_cause, reverse=True)
    ]
