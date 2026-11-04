"""Read the audit log. Admin only (enforced where the router is included)."""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import AuditLog

router = APIRouter()


@router.get("/")
async def list_audit_log(
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    username: Optional[str] = None,
    action: Optional[str] = None,
    case_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if username:
        query = query.filter(AuditLog.username.ilike(f"%{username}%"))
    if action:
        query = query.filter(AuditLog.action == action)
    if case_id:
        query = query.filter(AuditLog.case_id == case_id)
    if date_from:
        query = query.filter(AuditLog.created_at >= date_from)
    if date_to:
        query = query.filter(AuditLog.created_at < date_to + timedelta(days=1))
    total = query.count()
    rows = query.order_by(AuditLog.log_id.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "items": [
            {
                "log_id": r.log_id, "created_at": r.created_at, "username": r.username, "action": r.action,
                "entity_type": r.entity_type, "entity_id": r.entity_id, "case_id": r.case_id, "detail": r.detail,
            }
            for r in rows
        ],
        "total": total, "page": page, "size": size, "pages": (total + size - 1) // size,
    }
