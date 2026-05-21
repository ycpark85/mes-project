from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.permission import Permission
from app.models.user import User
from app.schemas.permission import PermissionListOut


router = APIRouter(prefix="/permissions", tags=["Permission"])


@router.get("", response_model=PermissionListOut)
def list_permissions(
    page: int = Query(1, ge=1),
    size: int = Query(200, ge=1, le=500),
    q: str | None = Query(None),
    is_active: bool | None = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Permission)

    if is_active is not None:
        query = query.filter(Permission.is_active == is_active)

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Permission.permission_code.ilike(like),
                Permission.menu_code.ilike(like),
                Permission.action_code.ilike(like),
                Permission.permission_name.ilike(like),
            )
        )

    total = query.with_entities(func.count()).scalar() or 0

    items = (
        query.order_by(
            Permission.sort_order.asc(),
            Permission.permission_code.asc(),
        )
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
    }