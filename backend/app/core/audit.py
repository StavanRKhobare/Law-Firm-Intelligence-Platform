"""Audit trail: who did what. Rows are added to the caller's transaction."""
import json
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models.models import AuditLog
from ..models.user import User


def record(
    db: Session,
    user: Optional[User],
    action: str,
    entity_type: str,
    entity_id=None,
    case_id: Optional[int] = None,
    detail=None,
) -> None:
    db.add(AuditLog(
        user_id=user.user_id if user else None,
        username=user.username if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=None if entity_id is None else str(entity_id),
        case_id=case_id,
        detail=json.dumps(detail, default=str) if isinstance(detail, (dict, list)) else detail,
    ))


def set_actor(db: Session, user: User) -> None:
    """Tell the status-audit trigger who is acting, for this transaction only (PostgreSQL)."""
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT set_config('app.current_user', :name, true)"), {"name": user.username})
