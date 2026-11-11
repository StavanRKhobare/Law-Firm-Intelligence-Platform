"""Who may do what. Every rule the API enforces about roles lives here.

admin   Everything.
staff   Sees every matter and can add hearings, tasks, notes and documents.
        Cannot edit a matter's core details, assign counsel, or delete.
lawyer  Full access to matters they are actively assigned to. Elsewhere they see
        only titles and numbers, which is what a conflict check needs.
"""
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.models import CaseLawyer, CaseClient, CaseOpposingParty, LegalCase
from ..models.user import User


def is_admin(user: User) -> bool:
    return user.role == "admin"


def sees_all_matters(user: User) -> bool:
    return user.role in ("admin", "staff")


def assigned_case_ids(user: User):
    """Subquery of the matters a user is actively assigned to."""
    return select(CaseLawyer.case_id).where(
        CaseLawyer.lawyer_id == user.lawyer_id,
        CaseLawyer.end_date.is_(None),
    )


def case_scope(user: User):
    """Filter clause limiting a LegalCase-joined query to what the user may open. None means no limit."""
    if sees_all_matters(user):
        return None
    if user.lawyer_id is None:
        return LegalCase.case_id.is_(None)
    return LegalCase.case_id.in_(assigned_case_ids(user))


@dataclass
class CaseAccess:
    view: bool = False      # open the matter and everything on it
    work: bool = False      # add hearings, tasks, notes, documents
    edit: bool = False      # change details and status
    assign: bool = False    # change counsel
    delete: bool = False


def case_access(db: Session, user: User, case_id: int) -> CaseAccess:
    if is_admin(user):
        return CaseAccess(True, True, True, True, True)
    if user.role == "staff":
        return CaseAccess(view=True, work=True)
    if user.lawyer_id is None:
        return CaseAccess()
    row = db.query(CaseLawyer).filter(
        CaseLawyer.case_id == case_id,
        CaseLawyer.lawyer_id == user.lawyer_id,
        CaseLawyer.end_date.is_(None),
    ).first()
    if not row:
        return CaseAccess()
    return CaseAccess(view=True, work=True, edit=True, assign=row.role == "Lead Counsel")


def require_case(db: Session, user: User, case_id: int, action: str = "view") -> LegalCase:
    """Return the matter, or raise 404 if it doesn't exist and 403 if the user may not do this."""
    case = db.query(LegalCase).filter(LegalCase.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Matter {case_id} not found")
    if not getattr(case_access(db, user, case_id), action):
        raise HTTPException(status_code=403, detail="You do not have access to do this on this matter")
    return case


def visible_client_ids(user: User):
    """Clients on the user's matters. None means every client."""
    if sees_all_matters(user):
        return None
    return select(CaseClient.client_id).where(CaseClient.case_id.in_(assigned_case_ids(user)))


def visible_party_ids(user: User):
    """Opposing parties on the user's matters. None means every party."""
    if sees_all_matters(user):
        return None
    return select(CaseOpposingParty.party_id).where(CaseOpposingParty.case_id.in_(assigned_case_ids(user)))


def can_view_lawyer_matters(user: User, lawyer_id: int) -> bool:
    return sees_all_matters(user) or user.lawyer_id == lawyer_id
