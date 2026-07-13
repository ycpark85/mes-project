from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.inspection_result import InspectionResult
from app.models.inspection_schedule import InspectionSchedule
from app.models.lot import Lot
from app.models.product_inventory import ProductInventory
from app.models.shipment_line import ShipmentLine
from app.schemas.inspection_schedule import (
    InspectionScheduleOut,
    InspectionStockLotListOut,
    InspectionStockLotOut,
)
from app.services.inventory_fifo_service import get_available_inventory_lots_fifo


def get_inspection_schedule_detail(
    db: Session,
    inspection_schedule_id: int,
) -> InspectionScheduleOut:
    schedule = db.get(InspectionSchedule, inspection_schedule_id)
    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection schedule not found",
        )

    return InspectionScheduleOut.model_validate(schedule, from_attributes=True)


def list_inspection_stock_lots(
    db: Session,
    inspection_schedule_id: int,
) -> InspectionStockLotListOut:
    schedule = db.get(InspectionSchedule, inspection_schedule_id)
    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection schedule not found",
        )

    current_lot = db.get(Lot, schedule.lot_id)
    if current_lot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lot not found",
        )

    current_result_id = db.execute(
        select(InspectionResult.inspection_result_id)
        .where(InspectionResult.inspection_schedule_id == inspection_schedule_id)
        .limit(1)
    ).scalar_one_or_none()

    inventory_total_qty = int(
        db.execute(
            select(func.coalesce(ProductInventory.current_qty, 0)).where(
                ProductInventory.product_id == current_lot.product_id
            )
        ).scalar_one_or_none()
        or 0
    )

    remaining_display_qty = max(inventory_total_qty, 0)
    items_by_lot_no: dict[str, InspectionStockLotOut] = {}

    for inventory_lot, stock_qty in get_available_inventory_lots_fifo(
        db,
        product_id=current_lot.product_id,
        exclude_lot_no=current_lot.lot_no,
        exclude_inspection_result_id=current_result_id,
    ):
        if remaining_display_qty <= 0:
            break

        display_qty = min(stock_qty, remaining_display_qty)
        if display_qty <= 0:
            continue

        stock_lot_id = db.execute(
            select(Lot.lot_id)
            .where(
                Lot.product_id == current_lot.product_id,
                Lot.lot_no == inventory_lot.lot_no,
            )
            .limit(1)
        ).scalar_one_or_none()

        items_by_lot_no[inventory_lot.lot_no] = InspectionStockLotOut(
            lot_id=stock_lot_id or inventory_lot.product_inventory_lot_id,
            lot_no=inventory_lot.lot_no,
            stock_qty=display_qty,
            allocated_ship_qty=0,
            created_date=inventory_lot.created_at,
        )
        remaining_display_qty -= display_qty

    if current_result_id is not None:
        current_stock_lines = db.execute(
            select(ShipmentLine).where(
                ShipmentLine.inspection_result_id == current_result_id,
                ShipmentLine.source_type == "STOCK",
                ShipmentLine.status != "CANCELED",
            )
        ).scalars().all()

        for line in current_stock_lines:
            lot_no = line.stock_lot_no or ""
            qty = int(line.ship_qty or line.shipped_qty or 0)
            if not lot_no or qty <= 0:
                continue

            if lot_no in items_by_lot_no:
                items_by_lot_no[lot_no].stock_qty += qty
                continue

            items_by_lot_no[lot_no] = InspectionStockLotOut(
                lot_id=int(line.lot_id or line.product_inventory_lot_id or 0),
                lot_no=lot_no,
                stock_qty=qty,
                allocated_ship_qty=0,
                created_date=None,
            )

    items = list(items_by_lot_no.values())
    return InspectionStockLotListOut(
        items=items,
        total_stock_qty=sum(item.stock_qty for item in items),
    )
