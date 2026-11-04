"""API routes for lawyers and practice groups."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from datetime import date, timedelta

from ..core.audit import record
from ..core.permissions import can_view_lawyer_matters
from ..core.security import get_current_active_user, require_role
from ..database import get_db
from ..models.models import Lawyer, PracticeGroup, CaseLawyer, Hearing, LegalCase, Evidence, Task
from ..models.user import User
from ..schemas.lawyer import (
    LawyerCreate, LawyerUpdate, LawyerResponse, LawyerDetailed,
    LawyerList, PaginatedLawyers, CaseBrief, PracticeGroupBrief, PracticeGroupCreate,
)

router = APIRouter()
groups_router = APIRouter()

ACTIVE = ("Filed", "Hearing", "Pending")


def get_lawyer_or_404(db: Session, lawyer_id: int) -> Lawyer:
    lawyer = db.query(Lawyer).filter(Lawyer.lawyer_id == lawyer_id).first()
    if not lawyer:
        raise HTTPException(status_code=404, detail=f"Lawyer {lawyer_id} not found")
    return lawyer


def active_assignments(lawyer: Lawyer):
    return [a for a in lawyer.assignments if a.end_date is None and a.legal_case is not None]


def check_bar_id_free(db: Session, bar_id: Optional[str], lawyer_id: Optional[int] = None) -> None:
    """400 if another lawyer already holds this bar enrolment number (bar_id is unique)."""
    if bar_id is None:
        return
    query = db.query(Lawyer).filter(Lawyer.bar_id == bar_id)
    if lawyer_id is not None:
        query = query.filter(Lawyer.lawyer_id != lawyer_id)
    if query.first():
        raise HTTPException(status_code=400, detail=f"Bar ID {bar_id} is already registered")


@router.post("/", response_model=LawyerResponse, status_code=status.HTTP_201_CREATED)
async def create_lawyer(
    data: LawyerCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(["admin"])),
):
    """A lawyer record without a login. To add someone who will sign in, use /team/members."""
    if data.group_id and not db.query(PracticeGroup).filter(PracticeGroup.group_id == data.group_id).first():
        raise HTTPException(status_code=404, detail=f"Practice group {data.group_id} not found")
    check_bar_id_free(db, data.bar_id)
    lawyer = Lawyer(**data.model_dump())
    db.add(lawyer)
    db.flush()
    record(db, admin, "lawyer_created", "lawyer", lawyer.lawyer_id)
    db.commit()
    db.refresh(lawyer)
    return lawyer


@router.get("/", response_model=PaginatedLawyers)
async def get_lawyers(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    group_id: Optional[int] = None,
    designation: Optional[str] = None,
    search: Optional[str] = None,
    active_only: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(Lawyer)
    if active_only:
        query = query.filter(Lawyer.is_active.is_(True))
    if group_id:
        query = query.filter(Lawyer.group_id == group_id)
    if designation:
        query = query.filter(Lawyer.designation == designation)
    if search:
        query = query.filter(or_(Lawyer.fname.ilike(f"%{search}%"), Lawyer.lname.ilike(f"%{search}%")))

    total = query.count()
    pages = (total + size - 1) // size
    lawyers = query.options(joinedload(Lawyer.practice_group)).order_by(
        Lawyer.is_active.desc(), Lawyer.fname, Lawyer.lname
    ).offset((page - 1) * size).limit(size).all()
    with_login = {row[0] for row in db.query(User.lawyer_id).filter(User.lawyer_id.isnot(None))}

    items = []
    for lawyer in lawyers:
        case_count = db.query(func.count(CaseLawyer.case_id)).filter(
            CaseLawyer.lawyer_id == lawyer.lawyer_id,
            CaseLawyer.end_date.is_(None),
        ).scalar() or 0
        items.append(LawyerList(
            lawyer_id=lawyer.lawyer_id,
            fname=lawyer.fname,
            lname=lawyer.lname,
            designation=lawyer.designation,
            group_name=lawyer.practice_group.group_name if lawyer.practice_group else None,
            total_cases=case_count,
            is_active=lawyer.is_active,
            has_login=lawyer.lawyer_id in with_login,
        ))
    return PaginatedLawyers(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{lawyer_id}", response_model=LawyerDetailed)
async def get_lawyer(
    lawyer_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    lawyer = db.query(Lawyer).options(
        joinedload(Lawyer.practice_group),
        joinedload(Lawyer.assignments).joinedload(CaseLawyer.legal_case),
    ).filter(Lawyer.lawyer_id == lawyer_id).first()
    if not lawyer:
        raise HTTPException(status_code=404, detail=f"Lawyer {lawyer_id} not found")

    login = db.query(User).filter(User.lawyer_id == lawyer_id).first()
    detail = LawyerDetailed(
        lawyer_id=lawyer.lawyer_id,
        fname=lawyer.fname,
        lname=lawyer.lname,
        designation=lawyer.designation,
        phoneno=lawyer.phoneno,
        bar_id=lawyer.bar_id,
        email=lawyer.email,
        joined_date=lawyer.joined_date,
        is_active=lawyer.is_active,
        group_id=lawyer.group_id,
        practice_group=lawyer.practice_group,
        has_login=login is not None,
    )
    if not can_view_lawyer_matters(user, lawyer_id):
        return detail

    current = sorted(active_assignments(lawyer), key=lambda a: a.legal_case.date_filed, reverse=True)
    case_ids = [a.case_id for a in current]
    today = date.today()
    detail.can_view_matters = True
    detail.total_cases = len(current)
    detail.active_cases = sum(1 for a in current if a.legal_case.status in ACTIVE)
    detail.disposed_cases = sum(1 for a in current if a.legal_case.status == "Disposed")
    detail.upcoming_hearings = db.query(func.count(Hearing.hearing_id)).filter(
        Hearing.case_id.in_(case_ids),
        Hearing.status == "Scheduled",
        Hearing.hearing_date.between(today, today + timedelta(days=14)),
    ).scalar() or 0
    if login:
        detail.overdue_tasks = db.query(func.count(Task.task_id)).filter(
            Task.assignee_id == login.user_id, Task.status != "Done", Task.due_date < today,
        ).scalar() or 0
    detail.matters = [
        CaseBrief(
            case_id=a.legal_case.case_id,
            matter_title=a.legal_case.matter_title,
            case_number=a.legal_case.case_number,
            status=a.legal_case.status,
            role=a.role,
            assigned_date=a.assigned_date,
        )
        for a in current
    ]
    return detail


@router.put("/{lawyer_id}", response_model=LawyerResponse)
async def update_lawyer(
    lawyer_id: int,
    data: LawyerUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Admins can edit anyone. A lawyer can edit their own contact details."""
    lawyer = get_lawyer_or_404(db, lawyer_id)
    changes = data.model_dump(exclude_unset=True)
    if user.role != "admin":
        if user.lawyer_id != lawyer_id:
            raise HTTPException(status_code=403, detail="You can only edit your own profile")
        if set(changes) - {"phoneno", "email"}:
            raise HTTPException(status_code=403, detail="Only an admin can change these details")
    if data.group_id is not None and not db.query(PracticeGroup).filter(PracticeGroup.group_id == data.group_id).first():
        raise HTTPException(status_code=404, detail=f"Practice group {data.group_id} not found")
    check_bar_id_free(db, data.bar_id, lawyer_id)
    for field, value in changes.items():
        setattr(lawyer, field, value)
    record(db, user, "lawyer_updated", "lawyer", lawyer_id, detail={"fields": sorted(changes)})
    db.commit()
    db.refresh(lawyer)
    return lawyer


@router.delete("/{lawyer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lawyer(
    lawyer_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(["admin"])),
):
    """Only for a record added by mistake. Deleting would erase their history on matters."""
    lawyer = get_lawyer_or_404(db, lawyer_id)
    if lawyer.assignments:
        raise HTTPException(status_code=409, detail="This lawyer has matter history. Deactivate them instead.")
    record(db, admin, "lawyer_deleted", "lawyer", lawyer_id, detail={"name": f"{lawyer.fname} {lawyer.lname}"})
    db.delete(lawyer)
    db.commit()


@router.get("/{lawyer_id}/cases", response_model=List[CaseBrief])
async def get_lawyer_cases(
    lawyer_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    get_lawyer_or_404(db, lawyer_id)
    if not can_view_lawyer_matters(user, lawyer_id):
        raise HTTPException(status_code=403, detail="You can only view your own matters")
    query = db.query(CaseLawyer).join(LegalCase).filter(
        CaseLawyer.lawyer_id == lawyer_id,
        CaseLawyer.end_date.is_(None),
    )
    if status_filter:
        query = query.filter(LegalCase.status == status_filter)
    rows = query.order_by(LegalCase.date_cause.desc()).all()
    return [
        CaseBrief(
            case_id=row.legal_case.case_id,
            matter_title=row.legal_case.matter_title,
            case_number=row.legal_case.case_number,
            status=row.legal_case.status,
            role=row.role,
            assigned_date=row.assigned_date,
        )
        for row in rows
    ]


@router.get("/{lawyer_id}/workload")
async def get_lawyer_workload(
    lawyer_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    if not can_view_lawyer_matters(user, lawyer_id):
        raise HTTPException(status_code=403, detail="You can only view your own workload")
    lawyer = db.query(Lawyer).options(
        joinedload(Lawyer.practice_group),
        joinedload(Lawyer.assignments).joinedload(CaseLawyer.legal_case),
    ).filter(Lawyer.lawyer_id == lawyer_id).first()
    if not lawyer:
        raise HTTPException(status_code=404, detail=f"Lawyer {lawyer_id} not found")

    current = active_assignments(lawyer)
    total = len(current)
    disposed = sum(1 for a in current if a.legal_case.status == "Disposed")
    evidence_count = db.query(func.count(Evidence.evidence_id)).filter(
        Evidence.lawyer_id == lawyer_id
    ).scalar() or 0
    return {
        "lawyer_id": lawyer_id,
        "lawyer_name": f"{lawyer.fname} {lawyer.lname}",
        "designation": lawyer.designation,
        "practice_group": lawyer.practice_group.group_name if lawyer.practice_group else None,
        "workload": {
            "total_cases": total,
            "filed": sum(1 for a in current if a.legal_case.status == "Filed"),
            "hearing": sum(1 for a in current if a.legal_case.status == "Hearing"),
            "pending": sum(1 for a in current if a.legal_case.status == "Pending"),
            "disposed": disposed,
        },
        "evidence_filed": evidence_count,
        "disposal_rate": round((disposed / total * 100), 2) if total else 0,
    }


@groups_router.get("/", response_model=List[PracticeGroupBrief])
async def list_practice_groups(db: Session = Depends(get_db)):
    return db.query(PracticeGroup).order_by(PracticeGroup.group_name).all()


@groups_router.post("/", response_model=PracticeGroupBrief, status_code=status.HTTP_201_CREATED)
async def create_practice_group(
    data: PracticeGroupCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(["admin"])),
):
    group = PracticeGroup(**data.model_dump())
    db.add(group)
    db.flush()
    record(db, admin, "practice_group_created", "practice_group", group.group_id, detail={"name": group.group_name})
    db.commit()
    db.refresh(group)
    return group
