from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserListOut,
    UserOut,
    UserResetPassword,
    UserRoleOptionOut,
    UserUpdate,
)
from app.services.user_management_query import (
    build_user_out,
    get_user_detail,
    list_role_options as list_role_options_query,
    list_users as list_users_query,
)
from app.services.user_management_service import (
    create_user as create_user_service,
    deactivate_user,
    reset_user_password as reset_user_password_service,
    update_user as update_user_service,
)


router = APIRouter(prefix="/users", tags=["User"])


@router.get("/role-options", response_model=list[UserRoleOptionOut])
def list_role_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("USERS.VIEW")),
):
    _ = current_user
    return list_role_options_query(db)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("USERS.CREATE")),
):
    _ = current_user
    try:
        user = create_user_service(db, payload)
        db.commit()
        db.refresh(user)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="login_id already exists",
        )

    return build_user_out(db, user)


@router.get("", response_model=UserListOut)
def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None),
    is_active: bool | None = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("USERS.VIEW")),
):
    _ = current_user
    return list_users_query(
        db,
        page=page,
        size=size,
        q=q,
        is_active=is_active,
    )


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("USERS.VIEW")),
):
    _ = current_user
    return get_user_detail(db, user_id, active_only=True)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int = Path(..., ge=1),
    payload: UserUpdate = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("USERS.UPDATE")),
):
    try:
        user = update_user_service(
            db,
            user_id,
            payload,
            current_user_id=current_user.user_id,
        )
        db.commit()
        db.refresh(user)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="user update conflict",
        )

    return build_user_out(db, user)


@router.patch("/{user_id}/reset-password", response_model=UserOut)
def reset_user_password(
    user_id: int = Path(..., ge=1),
    payload: UserResetPassword = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("USERS.RESET_PASSWORD")),
):
    _ = current_user
    try:
        user = reset_user_password_service(db, user_id, payload)
        db.commit()
        db.refresh(user)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="password reset conflict",
        )

    return build_user_out(db, user)


@router.delete("/{user_id}", response_model=UserOut)
def delete_user(
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("USERS.DELETE")),
):
    try:
        user = deactivate_user(
            db,
            user_id,
            current_user_id=current_user.user_id,
        )
        db.commit()
        db.refresh(user)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="user delete conflict",
        )

    return build_user_out(db, user)
