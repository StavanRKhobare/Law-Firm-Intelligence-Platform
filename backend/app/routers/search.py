"""Search across the firm, and the conflict-of-interest check."""
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..core.permissions import case_access, case_scope, visible_client_ids, visible_party_ids
from ..core.security import get_current_active_user
from ..database import get_db
from ..models.models import (
    CaseClient, CaseOpposingParty, Client, ClientPhoneNo, Evidence, Lawyer, LegalCase,
    OpposingParty, OpposingPartyPhoneNo,
)
from ..models.user import User

router = APIRouter()
conflicts_router = APIRouter()


def full_name(row) -> str:
    return f"{row.fname} {row.lname}".strip()


@router.get("/")
async def search(
    q: str = Query(..., min_length=2, max_length=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Up to 6 results per kind. Matters beyond the user's own are returned, marked as not openable."""
    like = f"%{q}%"
    results = {"matters": [], "clients": [], "parties": [], "lawyers": [], "documents": []}

    for case in db.query(LegalCase).filter(or_(
        LegalCase.matter_title.ilike(like), LegalCase.case_number.ilike(like),
    )).order_by(LegalCase.date_filed.desc()).limit(6):
        results["matters"].append({
            "id": case.case_id, "title": case.matter_title, "subtitle": f"{case.case_number} · {case.status}",
            "can_open": case_access(db, user, case.case_id).view,
        })

    visible = visible_client_ids(user)
    clients = db.query(Client).filter(or_(
        (Client.fname + " " + Client.lname).ilike(like), Client.email.ilike(like),
    )).limit(6).all()
    openable = None if visible is None else {r[0] for r in db.query(Client.client_id).filter(Client.client_id.in_(visible))}
    for client in clients:
        allowed = openable is None or client.client_id in openable
        results["clients"].append({
            "id": client.client_id, "title": full_name(client), "subtitle": "Client", "can_open": allowed,
        })

    visible = visible_party_ids(user)
    parties = db.query(OpposingParty).filter(or_(
        (OpposingParty.fname + " " + OpposingParty.lname).ilike(like), OpposingParty.email.ilike(like),
    )).limit(6).all()
    openable = None if visible is None else {r[0] for r in db.query(OpposingParty.party_id).filter(OpposingParty.party_id.in_(visible))}
    for party in parties:
        allowed = openable is None or party.party_id in openable
        results["parties"].append({
            "id": party.party_id, "title": full_name(party), "subtitle": "Opposing party", "can_open": allowed,
        })

    for lawyer in db.query(Lawyer).filter(or_(
        (Lawyer.fname + " " + Lawyer.lname).ilike(like), Lawyer.bar_id.ilike(like),
    )).limit(6):
        results["lawyers"].append({
            "id": lawyer.lawyer_id, "title": full_name(lawyer), "subtitle": lawyer.designation or "Lawyer", "can_open": True,
        })

    documents = db.query(Evidence).join(LegalCase, Evidence.case_id == LegalCase.case_id).filter(or_(
        Evidence.description.ilike(like), Evidence.file_name.ilike(like),
    ))
    scope = case_scope(user)
    if scope is not None:
        documents = documents.filter(scope)
    for doc in documents.limit(6):
        results["documents"].append({
            "id": doc.evidence_id, "case_id": doc.case_id, "title": doc.file_name or doc.description or f"Document {doc.evidence_id}",
            "subtitle": f"{doc.category} · {doc.legal_case.case_number}", "can_open": True,
        })
    return results


class Person(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=15)


class ConflictCheck(BaseModel):
    clients: List[Person] = []      # people we would act for
    parties: List[Person] = []      # people we would act against
    client_ids: List[int] = []
    party_ids: List[int] = []
    exclude_case_id: Optional[int] = None


def normalise(name: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def people_matching(db: Session, model, phone_model, id_column, person: Person):
    """Records with the same name, email or phone. Names ignore case and punctuation."""
    matches = {}
    target = normalise(person.name)
    if target:
        for row in db.query(model):
            if normalise(full_name(row)) == target:
                matches[getattr(row, id_column)] = (row, "same name")
    if person.email:
        for row in db.query(model).filter(func.lower(model.email) == person.email.lower()):
            matches.setdefault(getattr(row, id_column), (row, "same email"))
    if person.phone:
        ids = db.query(getattr(phone_model, id_column)).filter(phone_model.phoneno == person.phone)
        for row in db.query(model).filter(getattr(model, id_column).in_(ids)):
            matches.setdefault(getattr(row, id_column), (row, "same phone number"))
    return matches.values()


def matters_for(db: Session, link_model, id_column, record_id, exclude_case_id):
    query = db.query(LegalCase).join(link_model, link_model.case_id == LegalCase.case_id).filter(
        getattr(link_model, id_column) == record_id
    )
    if exclude_case_id:
        query = query.filter(LegalCase.case_id != exclude_case_id)
    return [
        {"case_id": c.case_id, "case_number": c.case_number, "matter_title": c.matter_title, "status": c.status}
        for c in query
    ]


@conflicts_router.post("/check")
async def check_conflicts(
    data: ConflictCheck,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Warn if a proposed client is adverse to the firm elsewhere, or a proposed opponent is a client.

    Matches exact names, emails and phones only. It is a prompt to check, not legal clearance.
    """
    proposed_clients = list(data.clients)
    for row in db.query(Client).filter(Client.client_id.in_(data.client_ids)):
        phone = row.phone_numbers[0].phoneno if row.phone_numbers else None
        proposed_clients.append(Person(name=full_name(row), email=row.email, phone=phone))
    proposed_parties = list(data.parties)
    for row in db.query(OpposingParty).filter(OpposingParty.party_id.in_(data.party_ids)):
        phone = row.phone_numbers[0].phoneno if row.phone_numbers else None
        proposed_parties.append(Person(name=full_name(row), email=row.email, phone=phone))

    hits = []
    for person in proposed_clients:
        for row, reason in people_matching(db, OpposingParty, OpposingPartyPhoneNo, "party_id", person):
            matters = matters_for(db, CaseOpposingParty, "party_id", row.party_id, data.exclude_case_id)
            if matters:
                hits.append({
                    "kind": "client_is_adverse",
                    "person": person.name,
                    "reason": reason,
                    "message": f"{person.name or full_name(row)} is an opposing party on {len(matters)} other matter(s), matched by {reason}.",
                    "matched_name": full_name(row),
                    "matters": matters,
                })
    for person in proposed_parties:
        for row, reason in people_matching(db, Client, ClientPhoneNo, "client_id", person):
            matters = matters_for(db, CaseClient, "client_id", row.client_id, data.exclude_case_id)
            if matters:
                hits.append({
                    "kind": "opponent_is_client",
                    "person": person.name,
                    "reason": reason,
                    "message": f"{person.name or full_name(row)} is a client of the firm on {len(matters)} matter(s), matched by {reason}.",
                    "matched_name": full_name(row),
                    "matters": matters,
                })
    return {"conflicts": hits}
