from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings


OLD_LOT_NO_PATTERN = re.compile(r"^CT(?P<yy>\d{2})(?P<mm>\d{2})(?P<dd>\d{2})0(?P<seq>\d{2})$")

MONTH_CODES = {
    "01": "A",
    "02": "B",
    "03": "C",
    "04": "D",
    "05": "E",
    "06": "F",
    "07": "G",
    "08": "H",
    "09": "I",
    "10": "J",
    "11": "K",
    "12": "L",
}


@dataclass(frozen=True)
class LotNoRewrite:
    lot_id: int
    old_lot_no: str
    new_lot_no: str


def convert_lot_no(lot_no: str) -> str | None:
    match = OLD_LOT_NO_PATTERN.match(lot_no)
    if not match:
        return None

    month_code = MONTH_CODES.get(match.group("mm"))
    if month_code is None:
        raise ValueError(f"Invalid month in lot_no={lot_no}")

    return f"CT{match.group('yy')}{month_code}{match.group('dd')}E{match.group('seq')}"


def load_rewrites(conn) -> list[LotNoRewrite]:
    rows = conn.execute(
        text("select lot_id, lot_no from lot order by lot_id asc")
    ).mappings()

    rewrites: list[LotNoRewrite] = []
    for row in rows:
        new_lot_no = convert_lot_no(row["lot_no"])
        if new_lot_no is None:
            continue

        rewrites.append(
            LotNoRewrite(
                lot_id=int(row["lot_id"]),
                old_lot_no=row["lot_no"],
                new_lot_no=new_lot_no,
            )
        )

    return rewrites


def validate_rewrites(conn, rewrites: list[LotNoRewrite]) -> None:
    new_lot_nos = [rewrite.new_lot_no for rewrite in rewrites]
    duplicate_new_lot_nos = sorted(
        {lot_no for lot_no in new_lot_nos if new_lot_nos.count(lot_no) > 1}
    )
    if duplicate_new_lot_nos:
        raise RuntimeError(
            "Duplicate converted lot_no values: " + ", ".join(duplicate_new_lot_nos)
        )

    target_lot_ids = {rewrite.lot_id for rewrite in rewrites}
    existing_rows = conn.execute(
        text("select lot_id, lot_no from lot where lot_no = any(:lot_nos)"),
        {"lot_nos": new_lot_nos},
    ).mappings()

    conflicts = [
        f"{row['lot_no']} already exists on lot_id={row['lot_id']}"
        for row in existing_rows
        if int(row["lot_id"]) not in target_lot_ids
    ]
    if conflicts:
        raise RuntimeError("Converted lot_no conflicts: " + "; ".join(conflicts))


def print_preview(rewrites: list[LotNoRewrite], limit: int) -> None:
    print(f"Target rows: {len(rewrites)}")
    for rewrite in rewrites[:limit]:
        print(f"{rewrite.lot_id}: {rewrite.old_lot_no} -> {rewrite.new_lot_no}")

    if len(rewrites) > limit:
        print(f"... {len(rewrites) - limit} more rows")


def apply_rewrites(conn, rewrites: list[LotNoRewrite]) -> None:
    # Avoid unique constraint conflicts while old/new values are being swapped.
    for rewrite in rewrites:
        temp_lot_no = f"__FIX{rewrite.lot_id:015d}"
        conn.execute(
            text("update lot set lot_no = :temp_lot_no where lot_id = :lot_id"),
            {"temp_lot_no": temp_lot_no, "lot_id": rewrite.lot_id},
        )

    for rewrite in rewrites:
        conn.execute(
            text("update lot set lot_no = :new_lot_no where lot_id = :lot_id"),
            {"new_lot_no": rewrite.new_lot_no, "lot_id": rewrite.lot_id},
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rewrite old LOT numbers from CTYYMMDD0NN to CTYY{A-L}DDE NN style."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply updates. Without this flag, only a dry-run preview is printed.",
    )
    parser.add_argument(
        "--preview-limit",
        type=int,
        default=30,
        help="Maximum number of rows to show in preview.",
    )
    args = parser.parse_args()

    engine = create_engine(settings.database_url)

    with engine.begin() as conn:
        rewrites = load_rewrites(conn)
        validate_rewrites(conn, rewrites)
        print_preview(rewrites, args.preview_limit)

        if not args.apply:
            print("Dry-run only. Re-run with --apply to update DB.")
            return

        apply_rewrites(conn, rewrites)
        print(f"Updated rows: {len(rewrites)}")


if __name__ == "__main__":
    main()
