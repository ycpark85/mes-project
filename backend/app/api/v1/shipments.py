from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.partner import Partner
from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.product_inventory_movement import ProductInventoryMovement
from app.models.inspection_result import InspectionResult
from app.models.inspection_schedule import InspectionSchedule
from app.models.shipment_coa import ShipmentCoa
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.routing_template_step import RoutingTemplateStep
from app.models.process import Process
from app.schemas.shipment_coa import ShipmentCoaOut, ShipmentCoaUpdateRequest
from app.models.shipment_line import ShipmentLine
from app.schemas.shipment import (
    ShipmentConfirmRequest,
    ShipmentConfirmResult,
    ShipmentLineListOut,
    ShipmentLineOut,
)
from app.services.ship_qty_policy import calculate_ship_qty


router = APIRouter(prefix="/shipments", tags=["Shipments"])


def _get_ship_target_qty(db: Session, order_line: OrderLine) -> int:
    partner = db.get(Partner, order_line.partner_id)
    partner_name = partner.name if partner else ""
    return int(calculate_ship_qty(partner_name, int(order_line.order_qty or 0)) or 0)


def _get_already_shipped_qty(db: Session, order_line_id: int) -> int:
    shipped_qty = db.execute(
        select(func.coalesce(func.sum(-ProductInventoryMovement.qty), 0)).where(
            ProductInventoryMovement.order_line_id == order_line_id,
            ProductInventoryMovement.movement_type == "SHIP_OUT",
        )
    ).scalar_one()

    return int(shipped_qty or 0)


def _sync_order_line_status_after_shipment(db: Session, order_line: OrderLine) -> None:
    if order_line.status in {"CANCELED", "DONE"}:
        return

    ship_target_qty = _get_ship_target_qty(db, order_line)
    already_shipped_qty = _get_already_shipped_qty(db, order_line.order_line_id)

    if already_shipped_qty >= ship_target_qty:
        order_line.status = "DONE"


@router.get("", response_model=ShipmentLineListOut)
def list_shipments(
    status: str = Query("WAITING"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    q: Optional[str] = Query(None),
    shipped_from: Optional[date] = Query(None),
    shipped_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    normalized_status = status.strip().upper()

    if normalized_status not in {"WAITING", "DONE", "CANCELED"}:
        raise HTTPException(status_code=422, detail="status must be WAITING, DONE, or CANCELED")

    base = (
        select(
            ShipmentLine,
            OrderLine.order_no.label("order_no"),
            Partner.name.label("partner_name"),
            Product.product_code.label("product_code"),
            Product.product_name.label("product_name"),
            Lot.lot_no.label("lot_no"),
        )
        .select_from(ShipmentLine)
        .join(OrderLine, OrderLine.order_line_id == ShipmentLine.order_line_id)
        .join(Partner, Partner.partner_id == OrderLine.partner_id)
        .join(Product, Product.product_id == ShipmentLine.product_id)
        .outerjoin(Lot, Lot.lot_id == ShipmentLine.lot_id)
        .where(ShipmentLine.status == normalized_status)
    )

    count_q = (
        select(func.count())
        .select_from(ShipmentLine)
        .join(OrderLine, OrderLine.order_line_id == ShipmentLine.order_line_id)
        .join(Partner, Partner.partner_id == OrderLine.partner_id)
        .join(Product, Product.product_id == ShipmentLine.product_id)
        .outerjoin(Lot, Lot.lot_id == ShipmentLine.lot_id)
        .where(ShipmentLine.status == normalized_status)
    )

    if q:
        keyword = f"%{q.strip()}%"
        search_cond = or_(
            OrderLine.order_no.ilike(keyword),
            Partner.name.ilike(keyword),
            Product.product_code.ilike(keyword),
            Product.product_name.ilike(keyword),
            Lot.lot_no.ilike(keyword),
        )
        base = base.where(search_cond)
        count_q = count_q.where(search_cond)
        
    if normalized_status == "DONE":
        if shipped_from is not None:
            shipped_from_dt = datetime.combine(shipped_from, time.min).replace(tzinfo=timezone.utc)
            base = base.where(ShipmentLine.shipped_at >= shipped_from_dt)
            count_q = count_q.where(ShipmentLine.shipped_at >= shipped_from_dt)

        if shipped_to is not None:
            shipped_to_dt = datetime.combine(shipped_to, time.max).replace(tzinfo=timezone.utc)
            base = base.where(ShipmentLine.shipped_at <= shipped_to_dt)
            count_q = count_q.where(ShipmentLine.shipped_at <= shipped_to_dt)
    total = int(db.execute(count_q).scalar_one() or 0)

    rows = (
        db.execute(
            base.order_by(
                ShipmentLine.created_at.desc(),
                ShipmentLine.shipment_line_id.desc(),
            )
            .limit(size)
            .offset((page - 1) * size)
        )
        .all()
    )

    items: list[ShipmentLineOut] = []

    for shipment_line, order_no, partner_name, product_code, product_name, lot_no in rows:
        order_line = db.get(OrderLine, shipment_line.order_line_id)

        ship_target_qty = 0
        already_shipped_qty = 0
        remaining_ship_qty = 0

        if order_line is not None:
            ship_target_qty = _get_ship_target_qty(db, order_line)
            already_shipped_qty = _get_already_shipped_qty(db, order_line.order_line_id)
            remaining_ship_qty = max(ship_target_qty - already_shipped_qty, 0)
        
        current_stock_qty = int(
            db.execute(
                select(func.coalesce(ProductInventory.current_qty, 0)).where(
                    ProductInventory.product_id == shipment_line.product_id
                )
            ).scalar_one()
            or 0
        )

        if normalized_status == "WAITING":
            stock_after_ship_qty = max(current_stock_qty - int(shipment_line.ship_qty or 0), 0)
        else:
            stock_after_ship_qty = current_stock_qty    

        items.append(
            ShipmentLineOut(
                shipment_line_id=shipment_line.shipment_line_id,
                order_line_id=shipment_line.order_line_id,
                order_no=order_no,
                partner_name=partner_name,
                product_id=shipment_line.product_id,
                product_code=product_code,
                product_name=product_name,
                lot_id=shipment_line.lot_id,
                lot_no=lot_no,
                inspection_result_id=shipment_line.inspection_result_id,
                source_type=shipment_line.source_type,
                status=shipment_line.status,
                ship_qty=shipment_line.ship_qty,
                shipped_qty=shipment_line.shipped_qty,
                ship_target_qty=ship_target_qty,
                already_shipped_qty=already_shipped_qty,
                remaining_ship_qty=remaining_ship_qty,
                current_stock_qty=current_stock_qty,
                stock_after_ship_qty=stock_after_ship_qty,
                memo=shipment_line.memo,
                created_at=shipment_line.created_at,
                shipped_at=shipment_line.shipped_at,
            )
        )

    return ShipmentLineListOut(
        items=items,
        total=total,
        page=page,
        size=size,
    )


@router.post("/confirm", response_model=ShipmentConfirmResult)
def confirm_shipments(
    payload: ShipmentConfirmRequest,
    db: Session = Depends(get_db),
):
    target_ids = sorted(set(payload.shipment_line_ids))

    lines = (
        db.execute(
            select(ShipmentLine)
            .where(
                ShipmentLine.shipment_line_id.in_(target_ids),
                ShipmentLine.status == "WAITING",
            )
            .with_for_update()
        )
        .scalars()
        .all()
    )

    if len(lines) != len(target_ids):
        raise HTTPException(status_code=409, detail="출하대기 상태가 아닌 항목이 포함되어 있습니다.")

    confirmed_ids: list[int] = []
    affected_order_line_ids: set[int] = set()

    try:
        for line in lines:
            ship_qty = int(line.ship_qty or 0)

            if ship_qty <= 0:
                raise HTTPException(status_code=422, detail="출하수량이 0인 항목은 출하할 수 없습니다.")

            inventory = (
                db.execute(
                    select(ProductInventory)
                    .where(ProductInventory.product_id == line.product_id)
                    .with_for_update()
                )
                .scalar_one_or_none()
            )

            if inventory is None:
                inventory = ProductInventory(
                    product_id=line.product_id,
                    current_qty=0,
                )
                db.add(inventory)
                db.flush()

            if int(inventory.current_qty or 0) < ship_qty:
                raise HTTPException(
                    status_code=409,
                    detail=f"재고가 부족합니다. shipment_line_id={line.shipment_line_id}",
                )

            inventory.current_qty -= ship_qty

            movement = ProductInventoryMovement(
                product_id=line.product_id,
                movement_type="SHIP_OUT",
                qty=-ship_qty,
                balance_after=inventory.current_qty,
                source_type="SHIPMENT_LINE",
                source_id=line.shipment_line_id,
                order_line_id=line.order_line_id,
                inspection_result_id=line.inspection_result_id,
                memo=f"출하관리 출하확정 / shipment_line_id={line.shipment_line_id}",
            )
            db.add(movement)

            line.shipped_qty = ship_qty
            line.status = "DONE"
            line.shipped_at = datetime.now(timezone.utc)

            confirmed_ids.append(line.shipment_line_id)
            affected_order_line_ids.add(line.order_line_id)

        for order_line_id in affected_order_line_ids:
            order_line = (
                db.execute(
                    select(OrderLine)
                    .where(OrderLine.order_line_id == order_line_id)
                    .with_for_update()
                )
                .scalar_one_or_none()
            )

            if order_line is not None:
                _sync_order_line_status_after_shipment(db, order_line)

        db.commit()

        return ShipmentConfirmResult(
            confirmed_count=len(confirmed_ids),
            confirmed_shipment_line_ids=confirmed_ids,
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

def _clean_text(value: Optional[str], default: str = "-") -> str:
    if value is None:
        return default

    normalized = value.strip()
    return normalized if normalized else default


def _append_unique(target: list[str], value: Optional[str]) -> None:
    if value is None:
        return

    normalized = value.strip()
    if not normalized:
        return

    if normalized not in target:
        target.append(normalized)


def _build_lot_text(values: list[str]) -> str:
    return ",\n".join(values) if values else "-"

def _is_printed_product(
    db: Session,
    product_id: int,
    lot_ids: list[int],
    outsource_work_group_ids: list[int],
) -> bool:
    if outsource_work_group_ids:
        actual_group = (
            db.execute(
                select(OutsourceWorkGroup.outsource_work_group_id)
                .where(
                    OutsourceWorkGroup.outsource_work_group_id.in_(outsource_work_group_ids),
                    func.upper(OutsourceWorkGroup.process_type) == "PRINT",
                )
                .limit(1)
            )
            .first()
        )

        if actual_group is not None:
            return True

    if lot_ids:
        actual_lot_group = (
            db.execute(
                select(OutsourceWorkGroup.outsource_work_group_id)
                .select_from(OutsourceWorkGroup)
                .join(
                    OutsourceWorkGroupItem,
                    OutsourceWorkGroupItem.outsource_work_group_id
                    == OutsourceWorkGroup.outsource_work_group_id,
                )
                .where(
                    OutsourceWorkGroupItem.lot_id.in_(lot_ids),
                    func.upper(OutsourceWorkGroup.process_type) == "PRINT",
                )
                .limit(1)
            )
            .first()
        )

        if actual_lot_group is not None:
            return True

    route_process = (
        db.execute(
            select(Process.process_id)
            .select_from(Product)
            .join(
                RoutingTemplateStep,
                RoutingTemplateStep.routing_template_id == Product.routing_template_id,
            )
            .join(Process, Process.process_id == RoutingTemplateStep.process_id)
            .where(
                Product.product_id == product_id,
                RoutingTemplateStep.is_active.is_(True),
                or_(
                    func.upper(Process.process_type) == "PRINT",
                    func.upper(Process.process_code).like("%PRINT%"),
                    Process.process_name.ilike("%인쇄%"),
                ),
            )
            .limit(1)
        )
        .first()
    )

    return route_process is not None

def _get_or_create_shipment_coa(db: Session, order_line_id: int) -> ShipmentCoa:
    existing = (
        db.execute(
            select(ShipmentCoa).where(ShipmentCoa.order_line_id == order_line_id)
        )
        .scalar_one_or_none()
    )

    if existing is not None:
        if existing.is_printed_product_snapshot is None:
            rows_for_print = (
                db.execute(
                    select(
                        ShipmentLine.lot_id,
                        InspectionSchedule.outsource_work_group_id,
                    )
                    .select_from(ShipmentLine)
                    .outerjoin(
                        InspectionResult,
                        InspectionResult.inspection_result_id
                        == ShipmentLine.inspection_result_id,
                    )
                    .outerjoin(
                        InspectionSchedule,
                        InspectionSchedule.inspection_schedule_id
                        == InspectionResult.inspection_schedule_id,
                    )
                    .where(
                        ShipmentLine.order_line_id == order_line_id,
                        ShipmentLine.status == "DONE",
                    )
                )
                .all()
            )

            lot_ids = sorted(
                {
                    int(lot_id)
                    for lot_id, _ in rows_for_print
                    if lot_id is not None
                }
            )

            outsource_work_group_ids = sorted(
                {
                    int(outsource_work_group_id)
                    for _, outsource_work_group_id in rows_for_print
                    if outsource_work_group_id is not None
                }
            )

            existing.is_printed_product_snapshot = _is_printed_product(
                db,
                existing.product_id,
                lot_ids,
                outsource_work_group_ids,
            )

            db.commit()
            db.refresh(existing)

        return existing

    rows = (
        db.execute(
            select(
                ShipmentLine,
                OrderLine,
                Product,
                Partner,
                Lot,
                InspectionSchedule,
            )
            .select_from(ShipmentLine)
            .join(OrderLine, OrderLine.order_line_id == ShipmentLine.order_line_id)
            .join(Product, Product.product_id == ShipmentLine.product_id)
            .join(Partner, Partner.partner_id == OrderLine.partner_id)
            .outerjoin(Lot, Lot.lot_id == ShipmentLine.lot_id)
            .outerjoin(
                InspectionResult,
                InspectionResult.inspection_result_id
                == ShipmentLine.inspection_result_id,
            )
            .outerjoin(
                InspectionSchedule,
                InspectionSchedule.inspection_schedule_id
                == InspectionResult.inspection_schedule_id,
            )
            .where(
                ShipmentLine.order_line_id == order_line_id,
                ShipmentLine.status == "DONE",
            )
            .order_by(ShipmentLine.shipment_line_id.asc())
        )
        .all()
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="출하완료된 COA 대상이 없습니다.",
        )

    first_line, first_order_line, first_product, first_partner, _, _ = rows[0]

    stock_lot_nos: list[str] = []
    production_lot_nos: list[str] = []
    inspection_dates: list[date] = []
    shipped_dates: list[date] = []
    lot_ids: list[int] = []
    outsource_work_group_ids: list[int] = []

    quantity_snapshot = 0

    for shipment_line, _, _, _, lot, inspection_schedule in rows:
        quantity_snapshot += int(
            shipment_line.shipped_qty
            or shipment_line.ship_qty
            or 0
        )

        if shipment_line.lot_id is not None and shipment_line.lot_id not in lot_ids:
            lot_ids.append(shipment_line.lot_id)

        if lot is not None:
            if shipment_line.source_type == "STOCK":
                _append_unique(stock_lot_nos, lot.lot_no)
            elif shipment_line.source_type == "INSPECTION_RESULT":
                _append_unique(production_lot_nos, lot.lot_no)

        if inspection_schedule is not None:
            if inspection_schedule.inspection_date is not None:
                inspection_dates.append(inspection_schedule.inspection_date)

            if (
                inspection_schedule.outsource_work_group_id is not None
                and inspection_schedule.outsource_work_group_id not in outsource_work_group_ids
            ):
                outsource_work_group_ids.append(inspection_schedule.outsource_work_group_id)

        if shipment_line.shipped_at is not None:
            shipped_dates.append(shipment_line.shipped_at.date())

    all_lot_nos = stock_lot_nos + production_lot_nos

    if inspection_dates:
        inspection_date_snapshot = max(inspection_dates)
    elif shipped_dates:
        inspection_date_snapshot = max(shipped_dates)
    else:
        inspection_date_snapshot = date.today()

    is_printed_product_snapshot = _is_printed_product(
        db,
        first_product.product_id,
        lot_ids,
        outsource_work_group_ids,
    )
    
    coa = ShipmentCoa(
        order_line_id=first_order_line.order_line_id,
        product_id=first_product.product_id,
        product_name_snapshot=_clean_text(first_product.product_name),
        product_spec_snapshot=_clean_text(first_product.product_spec),
        material_snapshot="COATED TYVEK",
        partner_name_snapshot=_clean_text(first_partner.name),
        lot_nos_snapshot=_build_lot_text(all_lot_nos),
        stock_lot_nos_snapshot=_build_lot_text(stock_lot_nos) if stock_lot_nos else None,
        production_lot_nos_snapshot=_build_lot_text(production_lot_nos) if production_lot_nos else None,
        quantity_snapshot=quantity_snapshot,
        inspection_date_snapshot=inspection_date_snapshot,
        is_printed_product_snapshot=is_printed_product_snapshot,
        memo=None,
    )

    db.add(coa)
    db.commit()
    db.refresh(coa)

    return coa


@router.get("/{order_line_id}/coa", response_model=ShipmentCoaOut)
def get_shipment_coa(
    order_line_id: int,
    db: Session = Depends(get_db),
):
    return _get_or_create_shipment_coa(db, order_line_id)


@router.patch("/{order_line_id}/coa", response_model=ShipmentCoaOut)
def update_shipment_coa(
    order_line_id: int,
    payload: ShipmentCoaUpdateRequest,
    db: Session = Depends(get_db),
):
    coa = _get_or_create_shipment_coa(db, order_line_id)

    coa.quantity_snapshot = payload.quantity_snapshot
    coa.inspection_date_snapshot = payload.inspection_date_snapshot
    coa.memo = payload.memo.strip() if payload.memo and payload.memo.strip() else None

    db.commit()
    db.refresh(coa)

    return coa