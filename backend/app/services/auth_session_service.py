from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_role import UserRole


def revoke_user_sessions(db: Session, user_id: int) -> None:
    db.execute(
        update(User)
        .where(User.user_id == user_id)
        .values(auth_version=User.auth_version + 1)
        .execution_options(synchronize_session="fetch")
    )


def revoke_role_user_sessions(db: Session, role_id: int) -> None:
    affected_user_ids = select(UserRole.user_id).where(UserRole.role_id == role_id)
    db.execute(
        update(User)
        .where(User.user_id.in_(affected_user_ids))
        .values(auth_version=User.auth_version + 1)
        .execution_options(synchronize_session="fetch")
    )
