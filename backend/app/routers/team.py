"""Team management: join requests, adding members, resetting access."""
import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from ..core.audit import record
from ..core.security import get_current_active_user, get_password_hash, require_role
from ..database import get_db
from ..models.models import JoinRequest, Lawyer, PracticeGroup, utcnow
from ..models.user import User
from ..schemas.auth import (
    DirectoryEntry,
    JoinRequestApprove,
    JoinRequestReject,
    JoinRequestResponse,
    MemberCreate,
    MemberCreated,
    MemberResponse,
    MemberRoleUpdate,
)

router = APIRouter()
admin_only = Depends(require_role(["admin"]))


def display_name(user: User) -> str:
    return user.full_name or user.username


def member_response(user: User) -> MemberResponse:
    response = MemberResponse.model_validate(user)
    if user.lawyer:
        response.lawyer_name = f"{user.lawyer.fname} {user.lawyer.lname}"
    return response


def check_identity_free(db: Session, username: str, email: str) -> None:
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username is already in use")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email is already in use")


def check_lawyer_fields_free(db: Session, bar_id: Optional[str], group_id: Optional[int]) -> None:
    if bar_id and db.query(Lawyer).filter(Lawyer.bar_id == bar_id).first():
        raise HTTPException(status_code=400, detail=f"Bar ID {bar_id} is already registered")
    if group_id and not db.get(PracticeGroup, group_id):
        raise HTTPException(status_code=404, detail=f"Practice group {group_id} not found")


def new_lawyer(fname, lname, email, phoneno, bar_id, designation, group_id) -> Lawyer:
    return Lawyer(
        fname=fname, lname=lname, email=email, phoneno=phoneno, bar_id=bar_id or None,
        designation=designation, group_id=group_id, joined_date=utcnow().date(), is_active=True,
    )


def get_member_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Member not found")
    return user


def ensure_not_last_admin(db: Session, user: User) -> None:
    if user.role == "admin" and user.is_active:
        others = db.query(User).filter(User.role == "admin", User.is_active.is_(True), User.user_id != user.user_id).count()
        if others == 0:
            raise HTTPException(status_code=400, detail="The firm must keep at least one active admin")


@router.get("/directory", response_model=List[DirectoryEntry])
async def directory(db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    """Active colleagues, for choosing who a task goes to."""
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name, User.username).all()
    return [DirectoryEntry(user_id=u.user_id, name=display_name(u), role=u.role, lawyer_id=u.lawyer_id) for u in users]


# ---------------------------------------------------------------------------
# Join requests
# ---------------------------------------------------------------------------

@router.get("/join-requests", response_model=List[JoinRequestResponse], dependencies=[admin_only])
async def list_join_requests(status: str = Query("Pending"), db: Session = Depends(get_db)):
    rows = db.query(JoinRequest).options(joinedload(JoinRequest.practice_group)).filter(
        JoinRequest.status == status
    ).order_by(JoinRequest.created_at.desc()).all()
    result = []
    for row in rows:
        item = JoinRequestResponse.model_validate(row)
        item.group_name = row.practice_group.group_name if row.practice_group else None
        result.append(item)
    return result


def get_pending_request(db: Session, request_id: int) -> JoinRequest:
    request = db.get(JoinRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Join request not found")
    if request.status != "Pending":
        raise HTTPException(status_code=409, detail=f"This request was already {request.status.lower()}")
    return request


@router.post("/join-requests/{request_id}/approve", response_model=MemberResponse)
async def approve_join_request(
    request_id: int,
    data: JoinRequestApprove,
    db: Session = Depends(get_db),
    admin: User = admin_only,
):
    """Create the account, and for a lawyer the lawyer record, from the request."""
    request = get_pending_request(db, request_id)
    check_identity_free(db, request.username, request.email)
    role = data.role or request.requested_role
    bar_id = data.bar_id if data.bar_id is not None else request.bar_id
    designation = data.designation if data.designation is not None else request.designation
    group_id = data.group_id if data.group_id is not None else request.group_id

    lawyer = None
    if role == "lawyer":
        check_lawyer_fields_free(db, bar_id, group_id)
        lawyer = new_lawyer(request.fname, request.lname, request.email, request.phoneno, bar_id, designation, group_id)
        db.add(lawyer)
        db.flush()

    user = User(
        username=request.username,
        email=request.email,
        hashed_password=request.hashed_password,
        full_name=f"{request.fname} {request.lname}",
        role=role,
        lawyer_id=lawyer.lawyer_id if lawyer else None,
    )
    db.add(user)
    db.flush()
    request.status = "Approved"
    request.reviewed_by = admin.user_id
    request.reviewed_at = utcnow()
    record(db, admin, "join_request_approved", "join_request", request_id, detail={"username": user.username, "role": role})
    db.commit()
    db.refresh(user)
    return member_response(user)


@router.post("/join-requests/{request_id}/reject", response_model=JoinRequestResponse)
async def reject_join_request(
    request_id: int,
    data: JoinRequestReject,
    db: Session = Depends(get_db),
    admin: User = admin_only,
):
    request = get_pending_request(db, request_id)
    request.status = "Rejected"
    request.review_note = data.note
    request.reviewed_by = admin.user_id
    request.reviewed_at = utcnow()
    record(db, admin, "join_request_rejected", "join_request", request_id, detail={"username": request.username})
    db.commit()
    db.refresh(request)
    return request


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------

@router.get("/members", response_model=List[MemberResponse], dependencies=[admin_only])
async def list_members(db: Session = Depends(get_db)):
    users = db.query(User).options(joinedload(User.lawyer)).order_by(User.is_active.desc(), User.full_name).all()
    return [member_response(u) for u in users]


@router.post("/members", response_model=MemberCreated, status_code=201)
async def create_member(data: MemberCreate, db: Session = Depends(get_db), admin: User = admin_only):
    """Add someone directly. They get a temporary password and must change it at first login."""
    check_identity_free(db, data.username, data.email)
    lawyer_id = data.lawyer_id
    if lawyer_id:
        lawyer = db.get(Lawyer, lawyer_id)
        if not lawyer:
            raise HTTPException(status_code=404, detail=f"Lawyer {lawyer_id} not found")
        if db.query(User).filter(User.lawyer_id == lawyer_id).first():
            raise HTTPException(status_code=400, detail="This lawyer already has a login")
    elif data.role == "lawyer":
        check_lawyer_fields_free(db, data.bar_id, data.group_id)
        lawyer = new_lawyer(data.fname, data.lname, data.email, data.phoneno, data.bar_id, data.designation, data.group_id)
        db.add(lawyer)
        db.flush()
        lawyer_id = lawyer.lawyer_id

    temporary_password = secrets.token_urlsafe(9)
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=get_password_hash(temporary_password),
        full_name=f"{data.fname} {data.lname}",
        role=data.role,
        lawyer_id=lawyer_id,
        must_change_password=True,
    )
    db.add(user)
    db.flush()
    record(db, admin, "member_created", "user", user.user_id, detail={"username": user.username, "role": user.role})
    db.commit()
    db.refresh(user)
    return MemberCreated(member=member_response(user), temporary_password=temporary_password)


@router.post("/members/{user_id}/reset-password")
async def reset_password(user_id: int, db: Session = Depends(get_db), admin: User = admin_only):
    user = get_member_or_404(db, user_id)
    temporary_password = secrets.token_urlsafe(9)
    user.hashed_password = get_password_hash(temporary_password)
    user.must_change_password = True
    record(db, admin, "password_reset", "user", user_id)
    db.commit()
    return {"temporary_password": temporary_password}


@router.patch("/members/{user_id}/role", response_model=MemberResponse)
async def change_role(user_id: int, data: MemberRoleUpdate, db: Session = Depends(get_db), admin: User = admin_only):
    user = get_member_or_404(db, user_id)
    if data.role != "admin":
        ensure_not_last_admin(db, user)
    if data.role == "lawyer" and not user.lawyer_id:
        fname, _, lname = (user.full_name or user.username).partition(" ")
        lawyer = new_lawyer(fname, lname or "-", user.email, None, None, None, None)
        db.add(lawyer)
        db.flush()
        user.lawyer_id = lawyer.lawyer_id
    record(db, admin, "role_changed", "user", user_id, detail={"from": user.role, "to": data.role})
    user.role = data.role
    db.commit()
    db.refresh(user)
    return member_response(user)


def set_active(db: Session, user: User, active: bool) -> None:
    user.is_active = active
    if user.lawyer:
        user.lawyer.is_active = active


@router.post("/members/{user_id}/deactivate", response_model=MemberResponse)
async def deactivate_member(user_id: int, db: Session = Depends(get_db), admin: User = admin_only):
    """Ends access at once. History stays. Their matters keep them until reassigned."""
    user = get_member_or_404(db, user_id)
    if user.user_id == admin.user_id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
    ensure_not_last_admin(db, user)
    set_active(db, user, False)
    record(db, admin, "member_deactivated", "user", user_id)
    db.commit()
    db.refresh(user)
    return member_response(user)


@router.post("/members/{user_id}/activate", response_model=MemberResponse)
async def activate_member(user_id: int, db: Session = Depends(get_db), admin: User = admin_only):
    user = get_member_or_404(db, user_id)
    set_active(db, user, True)
    record(db, admin, "member_activated", "user", user_id)
    db.commit()
    db.refresh(user)
    return member_response(user)
