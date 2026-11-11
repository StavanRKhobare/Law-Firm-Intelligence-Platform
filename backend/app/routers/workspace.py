"""The daily summary behind each person's dashboard."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..core.permissions import case_scope, is_admin
from ..core.security import get_current_active_user
from ..database import get_db
from ..models.models import CaseLawyer, CaseNote, Hearing, JoinRequest, LegalCase, Task
from ..models.user import User
from .hearings import hearing_response, list_query
from .tasks import task_response, visible_tasks

router = APIRouter()


@router.get("/summary")
async def summary(db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    """Admins and staff get the whole firm. A lawyer gets their own matters and work."""
    today = date.today()
    week_end = today + timedelta(days=7)
    scope = case_scope(user)

    matters = db.query(LegalCase)
    if scope is not None:
        matters = matters.filter(scope)
    open_matters = matters.filter(LegalCase.status != "Disposed")
    open_ids = select(LegalCase.case_id).where(LegalCase.status != "Disposed")
    if scope is not None:
        open_ids = open_ids.where(scope)
    has_next = select(Hearing.case_id).where(Hearing.status == "Scheduled", Hearing.hearing_date >= today)

    needs_date = open_matters.filter(LegalCase.case_id.notin_(has_next)).order_by(LegalCase.date_filed).limit(8).all()
    needs_date_total = open_matters.filter(LegalCase.case_id.notin_(has_next)).count()

    upcoming = list_query(db).filter(Hearing.status == "Scheduled", Hearing.hearing_date.between(today, week_end))
    # A hearing that has passed with nothing recorded still needs an outcome
    awaiting_result = list_query(db).filter(Hearing.status == "Scheduled", Hearing.hearing_date < today)
    if scope is not None:
        upcoming = upcoming.filter(scope)
        awaiting_result = awaiting_result.filter(scope)
    upcoming_rows = upcoming.order_by(Hearing.hearing_date, Hearing.hearing_time).limit(25).all()

    # Staff and admins see the firm's overdue work, but "my tasks" stays personal for everyone
    tasks = visible_tasks(db, user).filter(Task.status != "Done")
    my_tasks = tasks.filter(Task.assignee_id == user.user_id).options(
        joinedload(Task.assignee), joinedload(Task.legal_case)
    ).order_by(Task.due_date.is_(None), Task.due_date).limit(12).all()
    overdue = tasks.filter(Task.due_date < today)
    deadlines = tasks.filter(Task.kind != "Task", Task.due_date.between(today, today + timedelta(days=30))).options(
        joinedload(Task.assignee), joinedload(Task.legal_case)
    ).order_by(Task.due_date).limit(8).all()

    notes = db.query(CaseNote, LegalCase).join(LegalCase, CaseNote.case_id == LegalCase.case_id)
    if scope is not None:
        notes = notes.filter(scope)
    notes = notes.order_by(CaseNote.created_at.desc()).limit(6).all()

    response = {
        "role": user.role,
        "linked_to_lawyer": user.lawyer_id is not None,
        "counts": {
            "open_matters": open_matters.count(),
            "hearings_today": sum(1 for h in upcoming_rows if h.hearing_date == today),
            "hearings_this_week": upcoming.count(),
            "awaiting_result": awaiting_result.count(),
            "overdue_tasks": overdue.count(),
            "overdue_deadlines": overdue.filter(Task.kind != "Task").count(),
            "without_next_date": needs_date_total,
        },
        "hearings": [hearing_response(h) for h in upcoming_rows],
        "awaiting_result": [hearing_response(h) for h in awaiting_result.order_by(Hearing.hearing_date.desc()).limit(8).all()],
        "my_tasks": [task_response(t) for t in my_tasks],
        "deadlines": [task_response(t) for t in deadlines],
        "without_next_date": [
            {"case_id": c.case_id, "case_number": c.case_number, "matter_title": c.matter_title, "status": c.status}
            for c in needs_date
        ],
        "recent_notes": [
            {
                "note_id": n.note_id, "case_id": c.case_id, "case_number": c.case_number,
                "body": n.body, "author_name": n.author_name, "created_at": n.created_at,
            }
            for n, c in notes
        ],
    }
    if is_admin(user):
        response["pending_join_requests"] = db.query(JoinRequest).filter(JoinRequest.status == "Pending").count()
        response["unassigned_matters"] = db.query(func.count(LegalCase.case_id)).filter(
            LegalCase.status != "Disposed",
            LegalCase.case_id.notin_(
                select(CaseLawyer.case_id).where(CaseLawyer.role == "Lead Counsel", CaseLawyer.end_date.is_(None))
            ),
        ).scalar() or 0
    return response
