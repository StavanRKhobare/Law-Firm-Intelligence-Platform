"""API routes for lawyers and practice groups."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func

from ..database import get_db
from ..models.models import Lawyer, PracticeGroup, CaseLawyer, LegalCase, Evidence
from ..schemas.lawyer import (
    LawyerCreate, LawyerUpdate, LawyerResponse, LawyerDetailed,
    LawyerList, PaginatedLawyers, CaseBrief, PracticeGroupBrief,
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
async def create_lawyer(data: LawyerCreate, db: Session = Depends(get_db)):
    if data.group_id and not db.query(PracticeGroup).filter(PracticeGroup.group_id == data.group_id).first():
        raise HTTPException(status_code=404, detail=f"Practice group {data.group_id} not found")
    check_bar_id_free(db, data.bar_id)
    lawyer = Lawyer(**data.model_dump())
    db.add(lawyer)
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
    db: Session = Depends(get_db),
):
    query = db.query(Lawyer)
    if group_id:
        query = query.filter(Lawyer.group_id == group_id)
    if designation:
        query = query.filter(Lawyer.designation == designation)
    if search:
        query = query.filter(or_(Lawyer.fname.ilike(f"%{search}%"), Lawyer.lname.ilike(f"%{search}%")))

    total = query.count()
    pages = (total + size - 1) // size
    lawyers = query.options(joinedload(Lawyer.practice_group)).offset((page - 1) * size).limit(size).all()

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
        ))
    return PaginatedLawyers(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{lawyer_id}", response_model=LawyerDetailed)
async def get_lawyer(lawyer_id: int, db: Session = Depends(get_db)):
    lawyer = db.query(Lawyer).options(
        joinedload(Lawyer.practice_group),
        joinedload(Lawyer.assignments).joinedload(CaseLawyer.legal_case),
    ).filter(Lawyer.lawyer_id == lawyer_id).first()
    if not lawyer:
        raise HTTPException(status_code=404, detail=f"Lawyer {lawyer_id} not found")

    current = active_assignments(lawyer)
    recent = sorted(current, key=lambda a: a.legal_case.date_cause, reverse=True)[:5]
    return LawyerDetailed(
        lawyer_id=lawyer.lawyer_id,
        fname=lawyer.fname,
        lname=lawyer.lname,
        designation=lawyer.designation,
        phoneno=lawyer.phoneno,
        bar_id=lawyer.bar_id,
        group_id=lawyer.group_id,
        practice_group=lawyer.practice_group,
        total_cases=len(current),
        active_cases=sum(1 for a in current if a.legal_case.status in ACTIVE),
        disposed_cases=sum(1 for a in current if a.legal_case.status == "Disposed"),
        recent_cases=[
            CaseBrief(
                case_id=a.legal_case.case_id,
                matter_title=a.legal_case.matter_title,
                case_number=a.legal_case.case_number,
                status=a.legal_case.status,
                role=a.role,
                assigned_date=a.assigned_date,
            )
            for a in recent
        ],
    )


@router.put("/{lawyer_id}", response_model=LawyerResponse)
async def update_lawyer(lawyer_id: int, data: LawyerUpdate, db: Session = Depends(get_db)):
    lawyer = get_lawyer_or_404(db, lawyer_id)
    if data.group_id is not None and not db.query(PracticeGroup).filter(PracticeGroup.group_id == data.group_id).first():
        raise HTTPException(status_code=404, detail=f"Practice group {data.group_id} not found")
    check_bar_id_free(db, data.bar_id, lawyer_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(lawyer, field, value)
    db.commit()
    db.refresh(lawyer)
    return lawyer


@router.delete("/{lawyer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lawyer(lawyer_id: int, db: Session = Depends(get_db)):
    lawyer = get_lawyer_or_404(db, lawyer_id)
    db.delete(lawyer)
    db.commit()


@router.get("/{lawyer_id}/cases", response_model=List[CaseBrief])
async def get_lawyer_cases(
    lawyer_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    get_lawyer_or_404(db, lawyer_id)
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
async def get_lawyer_workload(lawyer_id: int, db: Session = Depends(get_db)):
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
