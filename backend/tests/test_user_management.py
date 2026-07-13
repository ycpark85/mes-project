from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import BigInteger, create_engine, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.partner import Partner
from app.models.role import Role
from app.models.user import User
from app.models.vendor_user_access import VendorUserAccess
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_management_query import build_user_out, list_users
from app.services.user_management_service import create_user, update_user


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, compiler, **kw):
    return "INTEGER"


TEST_TABLE_NAMES = [
    "partner",
    "users",
    "roles",
    "user_roles",
    "vendor_user_access",
]


class UserManagementTests(unittest.TestCase):
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
                    role_code="INACTIVE",
                    role_name="Inactive",
                    is_system=False,
                    is_active=False,
                ),
                Partner(
                    partner_id=1,
                    partner_type="VENDOR",
                    name="Vendor A",
                    business_no="V-001",
                    is_active=True,
                ),
            ]
        )
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_create_vendor_user_assigns_role_access_and_profile_defaults(self) -> None:
        payload = UserCreate(
            login_id=" vendor1 ",
            user_name=" Vendor User ",
            password="secret1",
            role_ids=[1, 1],
            is_vendor_user=True,
            vendor_partner_id=1,
        )

        with patch(
            "app.services.user_management_service.hash_password",
            return_value="hashed",
        ):
            user = create_user(self.db, payload)
        self.db.commit()

        result = build_user_out(self.db, user)

        self.assertEqual("vendor1", result.login_id)
        self.assertEqual("Vendor User", result.user_name)
        self.assertEqual("\uc678\uc8fc\uc5c5\uccb4", result.department)
        self.assertEqual("Vendor A", result.position)
        self.assertEqual(["ADMIN"], [role.role_code for role in result.roles])
        self.assertEqual(1, result.vendor_access.partner_id)

    def test_create_user_rejects_inactive_role(self) -> None:
        payload = UserCreate(
            login_id="user1",
            user_name="User",
            password="secret1",
            role_ids=[2],
        )

        with self.assertRaises(HTTPException) as ctx:
            create_user(self.db, payload)

        self.assertEqual(400, ctx.exception.status_code)

    def test_update_rejects_self_deactivation(self) -> None:
        user = User(
            user_id=1,
            login_id="admin",
            user_name="Admin",
            password_hash="hashed",
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            update_user(
                self.db,
                user.user_id,
                UserUpdate(is_active=False),
                current_user_id=user.user_id,
            )

        self.assertEqual(400, ctx.exception.status_code)

    def test_disabling_vendor_user_deactivates_vendor_access(self) -> None:
        user = User(
            user_id=1,
            login_id="vendor1",
            user_name="Vendor",
            password_hash="hashed",
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()
        self.db.add(
            VendorUserAccess(
                user_id=user.user_id,
                partner_id=1,
                is_active=True,
            )
        )
        self.db.commit()

        update_user(
            self.db,
            user.user_id,
            UserUpdate(is_vendor_user=False),
            current_user_id=99,
        )
        self.db.commit()

        access = self.db.execute(select(VendorUserAccess)).scalar_one()
        result = list_users(
            self.db,
            page=1,
            size=20,
            q=None,
            is_active=True,
        )

        self.assertFalse(access.is_active)
        self.assertIsNone(result.items[0].vendor_access)


if __name__ == "__main__":
    unittest.main()
