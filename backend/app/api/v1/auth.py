from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.auth_audit_log import AuthAuditLog
from app.core.auth import (
    create_access_token,
    get_current_user,
    get_user_permission_codes,
    get_user_roles,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.core.time import utc_now
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthChangePasswordRequest,
    AuthLoginRequest,
    AuthLoginResponse,
    AuthMeResponse,
    AuthRoleOut,
    AuthUserOut,
)


router = APIRouter(prefix="/auth", tags=["Auth"])

def _client_ip_from_request(request: Request) -> str | None:
    if request.client is None:
        return None

    return request.client.host


def _user_agent_from_request(request: Request) -> str | None:
    user_agent = request.headers.get("user-agent")

    if not user_agent:
        return None

    return user_agent[:500]


def _write_auth_audit_log(
    db: Session,
    *,
    event_type: str,
    request: Request,
    login_id: str | None,
    user_id: int | None,
    success: bool,
    reason: str | None = None,
) -> None:
    db.add(
        AuthAuditLog(
            event_type=event_type,
            login_id=login_id,
            user_id=user_id,
            success=success,
            reason=reason,
            client_ip=_client_ip_from_request(request),
            user_agent=_user_agent_from_request(request),
        )
    )

def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def _raise_if_login_temporarily_blocked(
    db: Session,
    *,
    request: Request,
    login_id: str,
) -> None:
    client_ip = _client_ip_from_request(request)
    now = utc_now()
    cutoff_at = now - timedelta(minutes=settings.AUTH_LOGIN_FAILURE_WINDOW_MINUTES)

    query = (
        db.query(
            func.count(AuthAuditLog.auth_audit_log_id),
            func.max(AuthAuditLog.created_at),
        )
        .filter(
            AuthAuditLog.event_type == "LOGIN_FAILED",
            AuthAuditLog.success == False,
            AuthAuditLog.login_id == login_id,
            AuthAuditLog.created_at >= cutoff_at,
        )
    )

    if client_ip:
        query = query.filter(AuthAuditLog.client_ip == client_ip)

    failed_count, last_failed_at = query.one()

    if failed_count < settings.AUTH_LOGIN_MAX_FAILED_ATTEMPTS:
        return

    if last_failed_at is None:
        return

    last_failed_at = _normalize_datetime(last_failed_at)
    lockout_until = last_failed_at + timedelta(
        minutes=settings.AUTH_LOGIN_LOCKOUT_MINUTES
    )

    remaining_seconds = int((lockout_until - now).total_seconds())

    if remaining_seconds <= 0:
        return

    _write_auth_audit_log(
        db,
        event_type="LOGIN_BLOCKED",
        request=request,
        login_id=login_id,
        user_id=None,
        success=False,
        reason="TOO_MANY_FAILED_ATTEMPTS",
    )
    db.commit()

    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=(
            "로그인 실패가 반복되어 잠시 차단되었습니다. "
            f"{max(1, remaining_seconds // 60)}분 후 다시 시도하세요."
        ),
        headers={"Retry-After": str(remaining_seconds)},
    )

@router.post("/login", response_model=AuthLoginResponse)
def login(
    payload: AuthLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    login_id = payload.login_id.strip()

    _raise_if_login_temporarily_blocked(
        db,
        request=request,
        login_id=login_id,
    )

    user = (
        db.query(User)
        .filter(
            User.login_id == login_id,
            User.is_active == True,
        )
        .first()
    )

    if user is None or not verify_password(payload.password, user.password_hash):
        _write_auth_audit_log(
            db,
            event_type="LOGIN_FAILED",
            request=request,
            login_id=login_id,
            user_id=user.user_id if user is not None else None,
            success=False,
            reason="INVALID_CREDENTIALS",
        )
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.last_login_at = utc_now()
    _write_auth_audit_log(
        db,
        event_type="LOGIN_SUCCESS",
        request=request,
        login_id=login_id,
        user_id=user.user_id,
        success=True,
        reason=None,
    )
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

@router.patch("/change-password", response_model=AuthMeResponse)
def change_password(
    payload: AuthChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 올바르지 않습니다.",
        )

    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="새 비밀번호는 현재 비밀번호와 달라야 합니다.",
        )

    current_user.password_hash = hash_password(payload.new_password)
    current_user.password_change_required = False

    _write_auth_audit_log(
        db,
        event_type="PASSWORD_CHANGED",
        request=request,
        login_id=current_user.login_id,
        user_id=current_user.user_id,
        success=True,
        reason=None,
    )

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    roles = get_user_roles(db, current_user.user_id)
    permissions = get_user_permission_codes(db, current_user.user_id)

    return {
        "user": AuthUserOut.model_validate(current_user),
        "roles": [AuthRoleOut.model_validate(role) for role in roles],
        "permissions": permissions,
    }
