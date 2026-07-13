from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.user import user_crud
from app.models.partner import Partner
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.vendor_user_access import VendorUserAccess
from app.schemas.user import (
    UserListOut,
    UserOut,
    UserRoleOptionOut,
    UserRoleOut,
    UserVendorAccessOut,
)


def list_role_options(db: Session) -> list[UserRoleOptionOut]:
    roles = db.execute(
        select(Role)
        .where(Role.is_active.is_(True))
        .order_by(Role.role_code.asc())
    ).scalars().all()

    return [
        UserRoleOptionOut(
            role_id=role.role_id,
            role_code=role.role_code,
            role_name=role.role_name,
        )
        for role in roles
    ]


def list_users(
    db: Session,
    *,
    page: int,
    size: int,
    q: str | None,
    is_active: bool | None,
) -> UserListOut:
    users, total = user_crud.list_paged(
        db,
        page=page,
        size=size,
        q=q,
        is_active=is_active,
    )

    return UserListOut(
        items=build_user_outs(db, users),
        total=total,
        page=page,
        size=size,
    )


def get_user_detail(
    db: Session,
    user_id: int,
    *,
    active_only: bool,
) -> UserOut:
    user = user_crud.get_or_404(db, user_id, active_only=active_only)
    return build_user_out(db, user)


def build_user_out(db: Session, user: User) -> UserOut:
    return build_user_outs(db, [user])[0]


def build_user_outs(db: Session, users: list[User]) -> list[UserOut]:
    if not users:
        return []

    user_ids = [int(user.user_id) for user in users]
    roles_by_user: dict[int, list[UserRoleOut]] = {user_id: [] for user_id in user_ids}
    role_rows = db.execute(
        select(UserRole.user_id, Role)
        .join(Role, Role.role_id == UserRole.role_id)
        .where(UserRole.user_id.in_(user_ids))
        .order_by(UserRole.user_id.asc(), Role.role_code.asc())
    ).all()

    for user_id, role in role_rows:
        roles_by_user[int(user_id)].append(
            UserRoleOut(
                role_id=role.role_id,
                role_code=role.role_code,
                role_name=role.role_name,
            )
        )

    vendor_access_by_user: dict[int, UserVendorAccessOut] = {}
    vendor_rows = db.execute(
        select(VendorUserAccess, Partner)
        .join(Partner, Partner.partner_id == VendorUserAccess.partner_id)
        .where(
            VendorUserAccess.user_id.in_(user_ids),
            VendorUserAccess.is_active.is_(True),
            Partner.partner_type == "VENDOR",
        )
        .order_by(
            VendorUserAccess.user_id.asc(),
            VendorUserAccess.updated_at.desc(),
        )
    ).all()

    for access, partner in vendor_rows:
        vendor_access_by_user.setdefault(
            int(access.user_id),
            UserVendorAccessOut(
                partner_id=partner.partner_id,
                partner_name=partner.name,
                is_active=access.is_active,
            ),
        )

    return [
        UserOut(
            user_id=user.user_id,
            login_id=user.login_id,
            user_name=user.user_name,
            department=user.department,
            position=user.position,
            is_active=user.is_active,
            password_change_required=user.password_change_required,
            last_login_at=user.last_login_at,
            created_at=getattr(user, "created_at", None),
            updated_at=getattr(user, "updated_at", None),
            roles=roles_by_user[int(user.user_id)],
            vendor_access=vendor_access_by_user.get(int(user.user_id)),
        )
        for user in users
    ]
