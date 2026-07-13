from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.outsource_legacy_status_audit import (
    audit_outsource_legacy_item_status,
    has_outsource_legacy_status_risk,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only audit for legacy outsource purchase-order item statuses "
            "before retiring deprecated item-level status APIs."
        )
    )
    parser.add_argument("--sample-limit", type=int, default=20)
    parser.add_argument(
        "--fail-on-risk",
        action="store_true",
        help="Exit with code 1 when legacy status dependency or drift is found.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = audit_outsource_legacy_item_status(
            db,
            sample_limit=args.sample_limit,
        )
        db.rollback()
    finally:
        db.close()

    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))

    if args.fail_on_risk and has_outsource_legacy_status_risk(report):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
