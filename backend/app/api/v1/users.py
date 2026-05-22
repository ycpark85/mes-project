from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, hash_password
from app.crud.user import user_crud
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.user import (
    UserCreate,
    UserListOut,
    UserOut,
    UserResetPassword,
    UserRoleOptionOut,
    UserRoleOut,
    UserUpdate,
)


router = APIRouter(prefix="/users", tags=["User"])


@router.get("/role-options", response_model=list[UserRoleOptionOut])
def list_role_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roles = (
        db.query(Role)
        .filter(Role.is_active == True)
        .order_by(Role.role_code.asc())
        .all()
    )

    return [
        UserRoleOptionOut(
            role_id=role.role_id,
            role_code=role.role_code,
            role_name=role.role_name,
        )
        for role in roles
    ]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role_ids = _validate_role_ids(db, payload.role_ids)

    login_id = _normalize_required(payload.login_id, "login_id")
    user_name = _normalize_required(payload.user_name, "user_name")

    obj = User(
        login_id=login_id,
        user_name=user_name,
        password_hash=hash_password(payload.password),
        password_change_required=True,
        department=_normalize_optional(payload.department),
        position=_normalize_optional(payload.position),
        is_active=payload.is_active,
    )

    try:
        db.add(obj)
        db.flush()

        _replace_user_roles(db, obj.user_id, role_ids)

        db.commit()
        db.refresh(obj)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="login_id already exists",
        )

    return _to_user_out(db, obj)


@router.get("", response_model=UserListOut)
def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
    is_active: bool | None = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = user_crud.list_paged(
        db,
        page=page,
        size=size,
        q=q,
        is_active=is_active,
    )

    return {
        "items": [_to_user_out(db, item) for item in items],
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    obj = user_crud.get_or_404(db, user_id, active_only=True)

    return _to_user_out(db, obj)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int = Path(..., ge=1),
    payload: UserUpdate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    obj = user_crud.get_or_404(db, user_id, active_only=False)

    if payload.user_name is not None:
        obj.user_name = _normalize_required(payload.user_name, "user_name")

    if payload.department is not None:
        obj.department = _normalize_optional(payload.department)

    if payload.position is not None:
        obj.position = _normalize_optional(payload.position)

    if payload.is_active is not None:
        if obj.user_id == current_user.user_id and payload.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="현재 로그인 사용자는 비활성화할 수 없습니다.",
            )

        obj.is_active = payload.is_active

    role_ids: list[int] | None = None
    if payload.role_ids is not None:
        role_ids = _validate_role_ids(db, payload.role_ids)

    try:
        db.add(obj)
        db.flush()

        if role_ids is not None:
            _replace_user_roles(db, obj.user_id, role_ids)

        db.commit()
        db.refresh(obj)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="user update conflict",
        )

    return _to_user_out(db, obj)


@router.patch("/{user_id}/reset-password", response_model=UserOut)
def reset_user_password(
    user_id: int = Path(..., ge=1),
    payload: UserResetPassword = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    obj = user_crud.get_or_404(db, user_id, active_only=False)

    obj.password_hash = hash_password(payload.new_password)
    obj.password_change_required = True

    updated = user_crud.commit(db, obj)

    return _to_user_out(db, updated)


@router.delete("/{user_id}", response_model=UserOut)
def delete_user(
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 로그인 사용자는 삭제할 수 없습니다.",
        )

    deleted = user_crud.soft_delete(db, user_id)

    return _to_user_out(db, deleted)


def _to_user_out(db: Session, obj: User) -> UserOut:
    roles = _get_user_roles(db, obj.user_id)

    return UserOut(
        user_id=obj.user_id,
        login_id=obj.login_id,
        user_name=obj.user_name,
        department=obj.department,
        position=obj.position,
        is_active=obj.is_active,
        password_change_required=obj.password_change_required,
        last_login_at=obj.last_login_at,
        created_at=getattr(obj, "created_at", None),
        updated_at=getattr(obj, "updated_at", None),
        roles=[
            UserRoleOut(
                role_id=role.role_id,
                role_code=role.role_code,
                role_name=role.role_name,
            )
            for role in roles
        ],
    )


def _get_user_roles(db: Session, user_id: int) -> list[Role]:
    return (
        db.query(Role)
        .join(UserRole, UserRole.role_id == Role.role_id)
        .filter(UserRole.user_id == user_id)
        .order_by(Role.role_code.asc())
        .all()
    )


def _validate_role_ids(db: Session, role_ids: list[int]) -> list[int]:
    unique_role_ids = sorted(set(role_ids or []))

    if not unique_role_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role_ids is required",
        )

    roles = (
        db.query(Role)
        .filter(
            Role.role_id.in_(unique_role_ids),
            Role.is_active == True,
        )
        .all()
    )

    if len(roles) != len(unique_role_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role_id not found",
        )

    return unique_role_ids


def _replace_user_roles(
    db: Session,
    user_id: int,
    role_ids: list[int],
) -> None:
    db.query(UserRole).filter(UserRole.user_id == user_id).delete(
        synchronize_session=False
    )

    for role_id in role_ids:
        db.add(
            UserRole(
                user_id=user_id,
                role_id=role_id,
            )
        )

    db.flush()


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