from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import (
    create_access_token,
    get_current_user,
    get_user_permission_codes,
    get_user_roles,
    verify_password,
)
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthLoginRequest,
    AuthLoginResponse,
    AuthMeResponse,
    AuthRoleOut,
    AuthUserOut,
)


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=AuthLoginResponse)
def login(
    payload: AuthLoginRequest,
    db: Session = Depends(get_db),
):
    login_id = payload.login_id.strip()

    user = (
        db.query(User)
        .filter(
            User.login_id == login_id,
            User.is_active == True,
        )
        .first()
    )

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(user)

    roles = get_user_roles(db, user.user_id)
    permissions = get_user_permission_codes(db, user.user_id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in_minutes": settings.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES,
        "user": AuthUserOut.model_validate(user),
        "roles": [AuthRoleOut.model_validate(role) for role in roles],
        "permissions": permissions,
    }


@router.get("/me", response_model=AuthMeResponse)
def me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(db, current_user.user_id)
    permissions = get_user_permission_codes(db, current_user.user_id)

    return {
        "user": AuthUserOut.model_validate(current_user),
        "roles": [AuthRoleOut.model_validate(role) for role in roles],
        "permissions": permissions,
    }