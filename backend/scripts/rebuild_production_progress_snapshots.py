from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.production_daily_query import rebuild_all_production_progress_snapshots


def main() -> int:
    db = SessionLocal()
    try:
        refreshed = rebuild_all_production_progress_snapshots(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"production_progress_snapshot rebuilt: {refreshed} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
