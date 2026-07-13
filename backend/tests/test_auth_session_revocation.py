from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import HTTPException, Request
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.api.v1.auth import change_password
from app.api.v1.roles import update_role_permissions
from app.core.auth import create_access_token, decode_access_token, get_current_user
from app.db.base import Base
from app.models.partner import Partner
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.auth import AuthChangePasswordRequest
from app.schemas.role import RolePermissionUpdate
from app.schemas.user import UserResetPassword, UserUpdate
from app.services.auth_session_service import (
    revoke_role_user_sessions,
    revoke_user_sessions,
)
from app.services.user_management_service import reset_user_password, update_user


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, compiler, **kw):
    return "INTEGER"


TEST_TABLE_NAMES = [
    "partner",
    "users",
    "roles",
    "user_roles",
    "permissions",
    "role_permissions",
    "vendor_user_access",
    "auth_audit_logs",
]


class AuthSessionRevocationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        tables = [Base.metadata.tables[name] for name in TEST_TABLE_NAMES]
        Base.metadata.create_all(self.engine, tables=tables)
        SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()
        self.db.add_all(
            [
                Role(
                    role_id=1,
                    role_code="ADMIN",
                    role_name="Administrator",
                    is_system=True,
                    is_active=True,
                ),
                Role(
                    role_id=2,
                    role_code="WORKER",
                    role_name="Worker",
                    is_system=False,
                    is_active=True,
                ),
                Partner(
                    partner_id=1,
                    partner_type="VENDOR",
                    name="Vendor A",
                    business_no="V-001",
                    is_active=True,
                ),
                Permission(
                    permission_id=1,
                    permission_code="TEST.VIEW",
                    menu_code="TEST",
                    action_code="VIEW",
                    permission_name="Test view",
                    sort_order=1,
                    is_active=True,
                ),
            ]
        )
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _add_user(self, user_id: int, login_id: str, role_id: int = 1) -> User:
        user = User(
            user_id=user_id,
            login_id=login_id,
            user_name=login_id,
            password_hash="hashed",
            auth_version=1,
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()
        self.db.add(UserRole(user_id=user_id, role_id=role_id))
        self.db.commit()
        self.db.refresh(user)
        return user

    def test_old_token_is_rejected_after_user_session_revocation(self) -> None:
        user = self._add_user(1, "user1")
        old_token = create_access_token(user)

        self.assertEqual(1, decode_access_token(old_token)["auth_version"])
        self.assertEqual(user.user_id, get_current_user(token=old_token, db=self.db).user_id)

        revoke_user_sessions(self.db, user.user_id)
        self.db.commit()
        self.db.refresh(user)

        self.assertEqual(2, user.auth_version)
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(token=old_token, db=self.db)
        self.assertEqual(401, ctx.exception.status_code)

        new_token = create_access_token(user)
        self.assertEqual(user.user_id, get_current_user(token=new_token, db=self.db).user_id)

    def test_password_change_rotates_current_session_token(self) -> None:
        user = self._add_user(1, "user1")
        old_token = create_access_token(user)
        request = Request(
            {
                "type": "http",
                "method": "PATCH",
                "path": "/api/v1/auth/change-password",
                "headers": [(b"user-agent", b"test-client")],
                "client": ("127.0.0.1", 12345),
            }
        )

        with (
            patch("app.api.v1.auth.verify_password", return_value=True),
            patch("app.api.v1.auth.hash_password", return_value="new-hash"),
        ):
            result = change_password(
                AuthChangePasswordRequest(
                    current_password="secret1",
                    new_password="secret2",
                ),
                request,
                current_user=user,
                db=self.db,
            )

        with self.assertRaises(HTTPException):
            get_current_user(token=old_token, db=self.db)
        self.assertEqual(
            user.user_id,
            get_current_user(token=result["access_token"], db=self.db).user_id,
        )
        self.assertFalse(result["user"].password_change_required)

    def test_identical_user_security_settings_do_not_revoke_token(self) -> None:
        user = self._add_user(1, "user1")

        update_user(
            self.db,
            user.user_id,
            UserUpdate(user_name="Updated", role_ids=[1]),
            current_user_id=99,
        )
        self.db.commit()
        self.db.refresh(user)

        self.assertEqual(1, user.auth_version)

    def test_role_change_and_password_reset_revoke_existing_tokens(self) -> None:
        user = self._add_user(1, "user1")

        update_user(
            self.db,
            user.user_id,
            UserUpdate(role_ids=[2]),
            current_user_id=99,
        )
        self.db.commit()
        self.db.refresh(user)
        self.assertEqual(2, user.auth_version)

        with patch(
            "app.services.user_management_service.hash_password",
            return_value="new-hash",
        ):
            reset_user_password(
                self.db,
                user.user_id,
                UserResetPassword(new_password="secret2"),
            )
        self.db.commit()
        self.db.refresh(user)

        self.assertEqual(3, user.auth_version)
        self.assertEqual("new-hash", user.password_hash)

    def test_vendor_access_change_revokes_existing_tokens(self) -> None:
        user = self._add_user(1, "vendor1")

        update_user(
            self.db,
            user.user_id,
            UserUpdate(
                is_vendor_user=True,
                vendor_partner_id=1,
                vendor_access_active=True,
            ),
            current_user_id=99,
        )
        self.db.commit()
        self.db.refresh(user)
        self.assertEqual(2, user.auth_version)

        update_user(
            self.db,
            user.user_id,
            UserUpdate(
                is_vendor_user=True,
                vendor_partner_id=1,
                vendor_access_active=True,
            ),
            current_user_id=99,
        )
        self.db.commit()
        self.db.refresh(user)
        self.assertEqual(2, user.auth_version)

    def test_role_revocation_only_updates_assigned_users(self) -> None:
        assigned_user = self._add_user(1, "assigned", role_id=2)
        other_user = self._add_user(2, "other", role_id=1)

        revoke_role_user_sessions(self.db, 2)
        self.db.commit()
        self.db.refresh(assigned_user)
        self.db.refresh(other_user)

        self.assertEqual(2, assigned_user.auth_version)
        self.assertEqual(1, other_user.auth_version)

    def test_role_permission_change_revokes_only_when_permissions_change(self) -> None:
        assigned_user = self._add_user(1, "assigned", role_id=2)
        current_user = self._add_user(2, "admin", role_id=1)

        update_role_permissions(
            role_id=2,
            payload=RolePermissionUpdate(permission_ids=[1]),
            db=self.db,
            current_user=current_user,
        )
        self.db.refresh(assigned_user)
        self.assertEqual(2, assigned_user.auth_version)

        update_role_permissions(
            role_id=2,
            payload=RolePermissionUpdate(permission_ids=[1]),
            db=self.db,
            current_user=current_user,
        )
        self.db.refresh(assigned_user)
        self.assertEqual(2, assigned_user.auth_version)


if __name__ == "__main__":
    unittest.main()
