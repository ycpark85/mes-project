from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import require_permission
from app.crud.role import role_crud
from app.db.session import get_db
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.schemas.role import (
    RoleCreate,
    RoleListOut,
    RoleOut,
    RolePermissionOut,
    RolePermissionUpdate,
    RoleUpdate,
)


router = APIRouter(prefix="/roles", tags=["Role"])


@router.post("", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("ROLES.CREATE")),
):
    role = Role(
        role_code=_normalize_code(payload.role_code),
        role_name=_normalize_required(payload.role_name, "role_name"),
        description=_normalize_optional(payload.description),
        is_system=False,
        is_active=payload.is_active,
    )

    try:
        db.add(role)
        db.commit()
        db.refresh(role)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="role_code already exists",
        )

    return role


@router.get("", response_model=RoleListOut)
def list_roles(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
    is_active: bool | None = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("ROLES.VIEW")),
):
    items, total = role_crud.list_paged(
        db,
        page=page,
        size=size,
        q=q,
        is_active=is_active,
        order_by_desc=False,
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/{role_id}", response_model=RoleOut)
def get_role(
    role_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("ROLES.VIEW")),
):
    return role_crud.get_or_404(db, role_id, active_only=True)


@router.patch("/{role_id}", response_model=RoleOut)
def update_role(
    role_id: int = Path(..., ge=1),
    payload: RoleUpdate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("ROLES.UPDATE")),
):
    role = role_crud.get_or_404(db, role_id, active_only=False)

    if payload.role_name is not None:
        role.role_name = _normalize_required(payload.role_name, "role_name")

    if payload.description is not None:
        role.description = _normalize_optional(payload.description)

    if payload.is_active is not None:
        if role.is_system and payload.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="시스템 역할은 비활성화할 수 없습니다.",
            )

        role.is_active = payload.is_active

    return role_crud.commit(db, role)


@router.delete("/{role_id}", response_model=RoleOut)
def delete_role(
    role_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("ROLES.DELETE")),
):
    role = role_crud.get_or_404(db, role_id, active_only=False)

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="시스템 역할은 삭제할 수 없습니다.",
        )

    return role_crud.soft_delete(db, role_id)


@router.get("/{role_id}/permissions", response_model=RolePermissionOut)
def get_role_permissions(
    role_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("ROLE_PERMISSIONS.VIEW")),
):
    role = role_crud.get_or_404(db, role_id, active_only=False)
    permissions = _get_role_permissions(db, role.role_id)

    return {
        "role_id": role.role_id,
        "permissions": permissions,
    }


@router.put("/{role_id}/permissions", response_model=RolePermissionOut)
def update_role_permissions(
    role_id: int = Path(..., ge=1),
    payload: RolePermissionUpdate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("ROLE_PERMISSIONS.UPDATE")),
):
    role = role_crud.get_or_404(db, role_id, active_only=False)

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="시스템 역할의 권한은 변경할 수 없습니다.",
        )

    permission_ids = _validate_permission_ids(db, payload.permission_ids)

    try:
        _replace_role_permissions(db, role.role_id, permission_ids)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="role permission update conflict",
        )

    permissions = _get_role_permissions(db, role.role_id)

    return {
        "role_id": role.role_id,
        "permissions": permissions,
    }


def _get_role_permissions(db: Session, role_id: int) -> list[Permission]:
    return (
        db.query(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.permission_id)
        .filter(
            RolePermission.role_id == role_id,
            Permission.is_active == True,
        )
        .order_by(
            Permission.sort_order.asc(),
            Permission.permission_code.asc(),
        )
        .all()
    )


def _validate_permission_ids(db: Session, permission_ids: list[int]) -> list[int]:
    unique_permission_ids = sorted(set(permission_ids or []))

    if not unique_permission_ids:
        return []

    permissions = (
        db.query(Permission)
        .filter(
            Permission.permission_id.in_(unique_permission_ids),
            Permission.is_active == True,
        )
        .all()
    )

    if len(permissions) != len(unique_permission_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="permission_id not found",
        )

    return unique_permission_ids


def _replace_role_permissions(
    db: Session,
    role_id: int,
    permission_ids: list[int],
) -> None:
    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete(
        synchronize_session=False
    )

    for permission_id in permission_ids:
        db.add(
            RolePermission(
                role_id=role_id,
                permission_id=permission_id,
            )
        )

    db.flush()


def _normalize_code(value: str) -> str:
    normalized = value.strip().upper()

    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role_code is required",
        )

    return normalized


def _normalize_required(value: str, field_name: str) -> str:
    normalized = value.strip()

    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is required",
        )

    return normalized


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()

    if not normalized:
        return None

    return normalized