from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.crud.user import user_crud
from app.models.partner import Partner
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.vendor_user_access import VendorUserAccess
from app.schemas.user import UserCreate, UserResetPassword, UserUpdate
from app.services.auth_session_service import revoke_user_sessions


def create_user(db: Session, payload: UserCreate) -> User:
    role_ids = _validate_role_ids(db, payload.role_ids)
    user = User(
        login_id=_normalize_required(payload.login_id, "login_id"),
        user_name=_normalize_required(payload.user_name, "user_name"),
        password_hash=hash_password(payload.password),
        password_change_required=True,
        department=_normalize_optional(payload.department),
        position=_normalize_optional(payload.position),
        is_active=payload.is_active,
    )

    db.add(user)
    db.flush()
    _replace_user_roles(db, user.user_id, role_ids)
    vendor_partner = _replace_vendor_access(
        db,
        user_id=user.user_id,
        is_vendor_user=payload.is_vendor_user,
        vendor_partner_id=payload.vendor_partner_id,
        vendor_access_active=payload.vendor_access_active,
    )
    _apply_vendor_profile_defaults(user, vendor_partner)
    db.flush()
    return user


def update_user(
    db: Session,
    user_id: int,
    payload: UserUpdate,
    *,
    current_user_id: int,
) -> User:
    user = user_crud.get_or_404(db, user_id, active_only=False)
    security_context_changed = False

    if payload.user_name is not None:
        user.user_name = _normalize_required(payload.user_name, "user_name")
    if payload.department is not None:
        user.department = _normalize_optional(payload.department)
    if payload.position is not None:
        user.position = _normalize_optional(payload.position)
    if payload.is_active is not None:
        if user.user_id == current_user_id and payload.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="\ud604\uc7ac \ub85c\uadf8\uc778 \uc0ac\uc6a9\uc790\ub294 \ube44\ud65c\uc131\ud654\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.",
            )
        if user.is_active != payload.is_active:
            user.is_active = payload.is_active
            security_context_changed = True

    if payload.role_ids is not None:
        role_ids = _validate_role_ids(db, payload.role_ids)
        existing_role_ids = set(
            db.execute(
                select(UserRole.role_id).where(UserRole.user_id == user.user_id)
            ).scalars()
        )
        if existing_role_ids != set(role_ids):
            _replace_user_roles(db, user.user_id, role_ids)
            security_context_changed = True

    if payload.is_vendor_user is not None:
        vendor_access_before = _get_vendor_access_state(db, user.user_id)
        vendor_partner = _replace_vendor_access(
            db,
            user_id=user.user_id,
            is_vendor_user=payload.is_vendor_user,
            vendor_partner_id=payload.vendor_partner_id,
            vendor_access_active=(
                payload.vendor_access_active
                if payload.vendor_access_active is not None
                else True
            ),
        )
        _apply_vendor_profile_defaults(user, vendor_partner)
        security_context_changed = (
            security_context_changed
            or vendor_access_before != _get_vendor_access_state(db, user.user_id)
        )

    db.flush()
    if security_context_changed:
        revoke_user_sessions(db, user.user_id)
    return user


def reset_user_password(
    db: Session,
    user_id: int,
    payload: UserResetPassword,
) -> User:
    user = user_crud.get_or_404(db, user_id, active_only=False)
    user.password_hash = hash_password(payload.new_password)
    user.password_change_required = True
    db.flush()
    revoke_user_sessions(db, user.user_id)
    return user


def deactivate_user(
    db: Session,
    user_id: int,
    *,
    current_user_id: int,
) -> User:
    if user_id == current_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="\ud604\uc7ac \ub85c\uadf8\uc778 \uc0ac\uc6a9\uc790\ub294 \uc0ad\uc81c\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.",
        )

    user = user_crud.get_or_404(db, user_id, active_only=False)
    if user.is_active:
        user.is_active = False
        db.flush()
        revoke_user_sessions(db, user.user_id)
    db.flush()
    return user


def _validate_role_ids(db: Session, role_ids: list[int]) -> list[int]:
    unique_role_ids = sorted(set(role_ids or []))
    if not unique_role_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role_ids is required",
        )

    existing_ids = set(
        db.execute(
            select(Role.role_id).where(
                Role.role_id.in_(unique_role_ids),
                Role.is_active.is_(True),
            )
        ).scalars()
    )
    if existing_ids != set(unique_role_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role_id not found",
        )

    return unique_role_ids


def _replace_user_roles(db: Session, user_id: int, role_ids: list[int]) -> None:
    db.execute(delete(UserRole).where(UserRole.user_id == user_id))
    db.add_all([UserRole(user_id=user_id, role_id=role_id) for role_id in role_ids])
    db.flush()


def _replace_vendor_access(
    db: Session,
    *,
    user_id: int,
    is_vendor_user: bool,
    vendor_partner_id: int | None,
    vendor_access_active: bool,
) -> Partner | None:
    existing_accesses = db.execute(
        select(VendorUserAccess).where(VendorUserAccess.user_id == user_id)
    ).scalars().all()

    if not is_vendor_user:
        for access in existing_accesses:
            access.is_active = False
        db.flush()
        return None

    if vendor_partner_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="\uc678\uc8fc\uc5c5\uccb4 \uacc4\uc815\uc740 \uc678\uc8fc\uc5c5\uccb4 \uac70\ub798\ucc98\ub97c \uc120\ud0dd\ud574\uc57c \ud569\ub2c8\ub2e4.",
        )

    partner = db.execute(
        select(Partner).where(
            Partner.partner_id == vendor_partner_id,
            Partner.partner_type == "VENDOR",
            Partner.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if partner is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="\ud65c\uc131 \uc678\uc8fc\uc5c5\uccb4 \uac70\ub798\ucc98\uac00 \uc544\ub2d9\ub2c8\ub2e4.",
        )

    target_access: VendorUserAccess | None = None
    for access in existing_accesses:
        if access.partner_id == vendor_partner_id:
            target_access = access
            access.is_active = vendor_access_active
        else:
            access.is_active = False

    if target_access is None:
        db.add(
            VendorUserAccess(
                user_id=user_id,
                partner_id=vendor_partner_id,
                is_active=vendor_access_active,
            )
        )

    db.flush()
    return partner


def _get_vendor_access_state(
    db: Session,
    user_id: int,
) -> tuple[tuple[int, bool], ...]:
    rows = db.execute(
        select(VendorUserAccess).where(VendorUserAccess.user_id == user_id)
    ).scalars().all()
    return tuple(sorted((int(row.partner_id), bool(row.is_active)) for row in rows))


def _apply_vendor_profile_defaults(user: User, partner: Partner | None) -> None:
    if partner is None:
        return
    if not user.department:
        user.department = "\uc678\uc8fc\uc5c5\uccb4"
    if not user.position:
        user.position = partner.name


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
    return value.strip() or None
