from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.auth import hash_password
from app.core.db import SessionLocal
from app.models.partner import Partner
from app.models.user import User
from app.models.vendor_user_access import VendorUserAccess


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create or update a vendor portal user and partner access.",
    )
    parser.add_argument("--login-id", required=True)
    parser.add_argument("--user-name", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--partner-id", required=True, type=int)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        partner = (
            db.query(Partner)
            .filter(
                Partner.partner_id == args.partner_id,
                Partner.partner_type == "VENDOR",
                Partner.is_active == True,
            )
            .first()
        )

        if partner is None:
            raise SystemExit(
                f"Active VENDOR partner not found: partner_id={args.partner_id}"
            )

        user = db.query(User).filter(User.login_id == args.login_id).first()
        if user is None:
            user = User(
                login_id=args.login_id,
                user_name=args.user_name,
                password_hash=hash_password(args.password),
                password_change_required=True,
                department="VENDOR",
                position=partner.name,
                is_active=True,
            )
            db.add(user)
            db.flush()
            action = "created"
        else:
            user.user_name = args.user_name
            user.password_hash = hash_password(args.password)
            user.password_change_required = True
            user.department = "VENDOR"
            user.position = partner.name
            user.is_active = True
            db.flush()
            action = "updated"

        access = (
            db.query(VendorUserAccess)
            .filter(
                VendorUserAccess.user_id == user.user_id,
                VendorUserAccess.partner_id == partner.partner_id,
            )
            .first()
        )

        if access is None:
            access = VendorUserAccess(
                user_id=user.user_id,
                partner_id=partner.partner_id,
                is_active=True,
            )
            db.add(access)
        else:
            access.is_active = True

        db.commit()
        print(
            f"Vendor portal user {action}: "
            f"login_id={user.login_id}, user_id={user.user_id}, "
            f"partner_id={partner.partner_id}, partner_name={partner.name}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
