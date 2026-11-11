"""Tasks and legal deadlines."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..core.audit import record
from ..core.permissions import assigned_case_ids, require_case, sees_all_matters
from ..core.security import get_current_active_user
from ..database import get_db
from ..models.models import Task, utcnow
from ..models.user import User
from ..schemas.work import PaginatedTasks, TaskCreate, TaskResponse, TaskUpdate

router = APIRouter()


def task_response(task: Task) -> TaskResponse:
    assignee = task.assignee
    return TaskResponse(
        task_id=task.task_id,
        title=task.title,
        description=task.description,
        kind=task.kind,
        priority=task.priority,
        status=task.status,
        due_date=task.due_date,
        overdue=bool(task.due_date and task.due_date < date.today() and task.status != "Done"),
        case_id=task.case_id,
        case_number=task.legal_case.case_number if task.legal_case else None,
        assignee_id=task.assignee_id,
        assignee_name=(assignee.full_name or assignee.username) if assignee else None,
        created_at=task.created_at,
        completed_at=task.completed_at,
    )


def visible_tasks(db: Session, user: User):
    """A lawyer sees work on their matters, plus anything given to them or created by them."""
    query = db.query(Task)
    if sees_all_matters(user):
        return query
    clauses = [Task.assignee_id == user.user_id, Task.created_by == user.user_id]
    if user.lawyer_id:
        clauses.append(Task.case_id.in_(assigned_case_ids(user)))
    return query.filter(or_(*clauses))


def get_task_or_404(db: Session, user: User, task_id: int) -> Task:
    task = visible_tasks(db, user).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


def check_assignee(db: Session, assignee_id: Optional[int]) -> None:
    if assignee_id:
        assignee = db.get(User, assignee_id)
        if not assignee or not assignee.is_active:
            raise HTTPException(status_code=404, detail="That person is not an active member")


@router.get("/", response_model=PaginatedTasks)
async def list_tasks(
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    case_id: Optional[int] = None,
    mine: bool = False,
    assignee_id: Optional[int] = None,
    kind: Optional[str] = None,
    open_only: bool = True,
    overdue: bool = False,
    deadlines_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    query = visible_tasks(db, user)
    if case_id:
        query = query.filter(Task.case_id == case_id)
    if mine:
        query = query.filter(Task.assignee_id == user.user_id)
    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)
    if kind:
        query = query.filter(Task.kind == kind)
    if deadlines_only:
        query = query.filter(Task.kind != "Task")
    if open_only:
        query = query.filter(Task.status != "Done")
    if overdue:
        query = query.filter(Task.due_date < date.today(), Task.status != "Done")
    total = query.count()
    rows = query.options(joinedload(Task.assignee), joinedload(Task.legal_case)).order_by(
        Task.due_date.is_(None), Task.due_date, Task.task_id
    ).offset((page - 1) * size).limit(size).all()
    return PaginatedTasks(items=[task_response(t) for t in rows], total=total, page=page, size=size, pages=(total + size - 1) // size)


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    if data.case_id:
        require_case(db, user, data.case_id, "work")
    check_assignee(db, data.assignee_id)
    task = Task(**data.model_dump(), created_by=user.user_id)
    task.assignee_id = data.assignee_id or user.user_id
    db.add(task)
    db.flush()
    record(db, user, "task_created", "task", task.task_id, data.case_id, {"title": data.title, "kind": data.kind})
    db.commit()
    db.refresh(task)
    return task_response(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    task = get_task_or_404(db, user, task_id)
    changes = data.model_dump(exclude_unset=True)
    check_assignee(db, changes.get("assignee_id"))
    kind = changes.get("kind", task.kind)
    due_date = changes.get("due_date", task.due_date)
    if kind != "Task" and due_date is None:
        raise HTTPException(status_code=400, detail="A legal deadline needs a due date")
    for field, value in changes.items():
        setattr(task, field, value)
    if "status" in changes:
        task.completed_at = utcnow() if changes["status"] == "Done" else None
    record(db, user, "task_updated", "task", task_id, task.case_id, {"fields": sorted(changes)})
    db.commit()
    db.refresh(task)
    return task_response(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    task = get_task_or_404(db, user, task_id)
    if user.role != "admin" and task.created_by != user.user_id:
        raise HTTPException(status_code=403, detail="Only the creator or an admin can delete a task")
    record(db, user, "task_deleted", "task", task_id, task.case_id, {"title": task.title})
    db.delete(task)
    db.commit()
