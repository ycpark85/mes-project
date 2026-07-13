from __future__ import annotations

from typing import Any

from sqlalchemy import and_, exists, func, literal, select
from sqlalchemy.orm import Session

from app.models.inspection_schedule import InspectionSchedule
from app.models.outsource_purchase_order_group import OutsourcePurchaseOrderGroup
from app.models.outsource_purchase_order_item import OutsourcePurchaseOrderItem
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_item import OutsourceWorkGroupItem


PROGRESS_STATUSES = ("VENDOR_RECEIVED", "WORK_DONE", "SHIPPED")
NULL_STATUS = "NULL"


def audit_outsource_legacy_item_status(
    db: Session,
    *,
    sample_limit: int = 20,
) -> dict[str, Any]:
    limit = max(sample_limit, 0)

    item_work_group_match_exists = (
        select(1)
        .select_from(OutsourceWorkGroup)
        .join(
            OutsourceWorkGroupItem,
            OutsourceWorkGroupItem.outsource_work_group_id
            == OutsourceWorkGroup.outsource_work_group_id,
        )
        .where(
            OutsourceWorkGroup.outsource_work_instruction_id
            == OutsourcePurchaseOrderItem.outsource_work_instruction_id,
            OutsourceWorkGroupItem.lot_id == OutsourcePurchaseOrderItem.lot_id,
        )
    )

    item_group_mismatch_base = (
        select(
            OutsourcePurchaseOrderItem.outsource_purchase_order_item_id.label(
                "purchase_order_item_id"
            ),
            OutsourcePurchaseOrderItem.outsource_purchase_order_id.label(
                "purchase_order_id"
            ),
            OutsourcePurchaseOrderItem.lot_id,
            OutsourcePurchaseOrderItem.outsource_work_instruction_id.label(
                "work_instruction_id"
            ),
            OutsourcePurchaseOrderItem.status.label("item_status"),
            OutsourceWorkGroup.outsource_work_group_id.label("work_group_id"),
            OutsourceWorkGroup.status.label("work_group_status"),
            OutsourcePurchaseOrderGroup.status.label("purchase_order_group_status"),
        )
        .select_from(OutsourcePurchaseOrderItem)
        .join(
            OutsourceWorkGroup,
            OutsourceWorkGroup.outsource_work_instruction_id
            == OutsourcePurchaseOrderItem.outsource_work_instruction_id,
        )
        .join(
            OutsourceWorkGroupItem,
            and_(
                OutsourceWorkGroupItem.outsource_work_group_id
                == OutsourceWorkGroup.outsource_work_group_id,
                OutsourceWorkGroupItem.lot_id == OutsourcePurchaseOrderItem.lot_id,
            ),
        )
        .outerjoin(
            OutsourcePurchaseOrderGroup,
            and_(
                OutsourcePurchaseOrderGroup.outsource_purchase_order_id
                == OutsourcePurchaseOrderItem.outsource_purchase_order_id,
                OutsourcePurchaseOrderGroup.outsource_work_group_id
                == OutsourceWorkGroup.outsource_work_group_id,
            ),
        )
        .where(
            func.coalesce(OutsourcePurchaseOrderItem.status, NULL_STATUS)
            != func.coalesce(OutsourceWorkGroup.status, NULL_STATUS)
        )
    )

    group_status_mismatch_base = (
        select(
            OutsourcePurchaseOrderGroup.outsource_purchase_order_group_id.label(
                "purchase_order_group_id"
            ),
            OutsourcePurchaseOrderGroup.outsource_purchase_order_id.label(
                "purchase_order_id"
            ),
            OutsourcePurchaseOrderGroup.outsource_work_group_id.label("work_group_id"),
            OutsourcePurchaseOrderGroup.status.label("purchase_order_group_status"),
            OutsourceWorkGroup.status.label("work_group_status"),
        )
        .select_from(OutsourcePurchaseOrderGroup)
        .join(
            OutsourceWorkGroup,
            OutsourceWorkGroup.outsource_work_group_id
            == OutsourcePurchaseOrderGroup.outsource_work_group_id,
        )
        .where(
            func.coalesce(OutsourcePurchaseOrderGroup.status, NULL_STATUS)
            != func.coalesce(OutsourceWorkGroup.status, NULL_STATUS)
        )
    )

    fallback_schedule_exists = exists(
        select(1)
        .select_from(OutsourcePurchaseOrderItem)
        .where(
            OutsourcePurchaseOrderItem.lot_id == InspectionSchedule.lot_id,
            OutsourcePurchaseOrderItem.status == "SHIPPED",
        )
    )

    return {
        "status_counts": {
            "purchase_order_item": _status_counts(
                db,
                OutsourcePurchaseOrderItem.status,
            ),
            "purchase_order_group": _status_counts(
                db,
                OutsourcePurchaseOrderGroup.status,
            ),
            "work_group": _status_counts(
                db,
                OutsourceWorkGroup.status,
            ),
        },
        "progressed_purchase_order_item_count": _scalar_count(
            db,
            select(func.count())
            .select_from(OutsourcePurchaseOrderItem)
            .where(OutsourcePurchaseOrderItem.status.in_(PROGRESS_STATUSES)),
        ),
        "purchase_order_item_without_work_group_match_count": _scalar_count(
            db,
            select(func.count())
            .select_from(OutsourcePurchaseOrderItem)
            .where(~exists(item_work_group_match_exists)),
        ),
        "item_work_group_status_mismatch_count": _count_subquery(
            db,
            item_group_mismatch_base,
        ),
        "purchase_order_group_status_mismatch_count": _count_subquery(
            db,
            group_status_mismatch_base,
        ),
        "legacy_schedule_fallback_count": _scalar_count(
            db,
            select(func.count())
            .select_from(InspectionSchedule)
            .where(
                InspectionSchedule.outsource_work_group_id.is_(None),
                InspectionSchedule.status != "CANCELED",
                fallback_schedule_exists,
            ),
        ),
        "active_schedule_without_work_group_count": _scalar_count(
            db,
            select(func.count())
            .select_from(InspectionSchedule)
            .where(
                InspectionSchedule.outsource_work_group_id.is_(None),
                InspectionSchedule.status != "CANCELED",
            ),
        ),
        "item_work_group_status_mismatch_samples": _sample_rows(
            db,
            item_group_mismatch_base.order_by(
                OutsourcePurchaseOrderItem.outsource_purchase_order_item_id.asc()
            ),
            limit=limit,
        ),
        "purchase_order_group_status_mismatch_samples": _sample_rows(
            db,
            group_status_mismatch_base.order_by(
                OutsourcePurchaseOrderGroup.outsource_purchase_order_group_id.asc()
            ),
            limit=limit,
        ),
        "purchase_order_item_without_work_group_match_samples": _sample_rows(
            db,
            select(
                OutsourcePurchaseOrderItem.outsource_purchase_order_item_id.label(
                    "purchase_order_item_id"
                ),
                OutsourcePurchaseOrderItem.outsource_purchase_order_id.label(
                    "purchase_order_id"
                ),
                OutsourcePurchaseOrderItem.lot_id,
                OutsourcePurchaseOrderItem.outsource_work_instruction_id.label(
                    "work_instruction_id"
                ),
                OutsourcePurchaseOrderItem.status.label("item_status"),
            )
            .where(~exists(item_work_group_match_exists))
            .order_by(OutsourcePurchaseOrderItem.outsource_purchase_order_item_id.asc()),
            limit=limit,
        ),
    }


def has_outsource_legacy_status_risk(report: dict[str, Any]) -> bool:
    return any(
        int(report.get(key) or 0) > 0
        for key in (
            "progressed_purchase_order_item_count",
            "purchase_order_item_without_work_group_match_count",
            "item_work_group_status_mismatch_count",
            "purchase_order_group_status_mismatch_count",
            "legacy_schedule_fallback_count",
        )
    )


def _status_counts(db: Session, status_column) -> dict[str, int]:
    status_expr = func.coalesce(status_column, literal(NULL_STATUS))
    rows = db.execute(
        select(
            status_expr.label("status"),
            func.count().label("count"),
        )
        .group_by(status_expr)
        .order_by(status_expr.asc())
    ).all()
    return {str(status): int(count or 0) for status, count in rows}


def _scalar_count(db: Session, stmt) -> int:
    return int(db.execute(stmt).scalar_one() or 0)


def _count_subquery(db: Session, stmt) -> int:
    return _scalar_count(db, select(func.count()).select_from(stmt.subquery()))


def _sample_rows(db: Session, stmt, *, limit: int) -> list[dict[str, Any]]:
    if limit == 0:
        return []
    return [dict(row) for row in db.execute(stmt.limit(limit)).mappings().all()]
