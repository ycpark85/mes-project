from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.partner import Partner
from app.models.raw_material import RawMaterial
from app.models.raw_material_inventory import RawMaterialInventory
from app.models.raw_material_inventory_lot import RawMaterialInventoryLot
from app.models.raw_material_inventory_movement import RawMaterialInventoryMovement
from app.models.raw_material_location import RawMaterialLocation
from app.schemas.raw_material import (
    RawMaterialInventoryLotListOut,
    RawMaterialInventoryLotOut,
    RawMaterialListOut,
    RawMaterialLocationListOut,
    RawMaterialLocationOut,
    RawMaterialMovementListOut,
    RawMaterialMovementOut,
    RawMaterialOut,
)


def _q2(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _q4(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _amount(qty: Decimal, unit_cost: Decimal | None) -> Decimal | None:
    if unit_cost is None:
        return None
    return (abs(_q2(qty)) * _q4(unit_cost)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _movement_out(row) -> RawMaterialMovementOut:
    return RawMaterialMovementOut(**dict(row))


def list_raw_materials_for_grid(
    db: Session,
    *,
    page: int = 1,
    size: int = 100,
    q: str | None = None,
    is_active: bool | None = True,
) -> RawMaterialListOut:
    current_qty_sq = (
        select(
            RawMaterialInventory.raw_material_id,
            func.coalesce(func.sum(RawMaterialInventory.current_qty), 0).label("current_qty"),
        )
        .group_by(RawMaterialInventory.raw_material_id)
        .subquery()
    )
    stmt = (
        select(RawMaterial, func.coalesce(current_qty_sq.c.current_qty, 0).label("current_qty"))
        .outerjoin(current_qty_sq, current_qty_sq.c.raw_material_id == RawMaterial.raw_material_id)
    )
    count_stmt = select(func.count()).select_from(RawMaterial)

    if is_active is not None:
        stmt = stmt.where(RawMaterial.is_active == is_active)
        count_stmt = count_stmt.where(RawMaterial.is_active == is_active)
    if q and q.strip():
        keyword = f"%{q.strip()}%"
        condition = or_(RawMaterial.material_code.ilike(keyword), RawMaterial.material_name.ilike(keyword))
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    total = int(db.execute(count_stmt).scalar_one() or 0)
    rows = db.execute(
        stmt.order_by(RawMaterial.material_code.asc()).limit(size).offset((page - 1) * size)
    ).all()
    items = []
    for material, current_qty in rows:
        out = RawMaterialOut.model_validate(material, from_attributes=True)
        out.current_qty = _q2(Decimal(current_qty or 0))
        items.append(out)
    return RawMaterialListOut(items=items, total=total, page=page, size=size)


def list_raw_material_locations_for_grid(
    db: Session,
    *,
    page: int = 1,
    size: int = 100,
    q: str | None = None,
    is_active: bool | None = True,
) -> RawMaterialLocationListOut:
    current_qty_sq = (
        select(
            RawMaterialInventory.raw_material_location_id,
            func.coalesce(func.sum(RawMaterialInventory.current_qty), 0).label("current_qty"),
        )
        .group_by(RawMaterialInventory.raw_material_location_id)
        .subquery()
    )
    stmt = (
        select(
            RawMaterialLocation,
            Partner.name.label("partner_name"),
            func.coalesce(current_qty_sq.c.current_qty, 0).label("current_qty"),
        )
        .outerjoin(Partner, Partner.partner_id == RawMaterialLocation.partner_id)
        .outerjoin(
            current_qty_sq,
            current_qty_sq.c.raw_material_location_id == RawMaterialLocation.raw_material_location_id,
        )
    )
    count_stmt = select(func.count()).select_from(RawMaterialLocation)
    if is_active is not None:
        stmt = stmt.where(RawMaterialLocation.is_active == is_active)
        count_stmt = count_stmt.where(RawMaterialLocation.is_active == is_active)
    if q and q.strip():
        keyword = f"%{q.strip()}%"
        condition = or_(
            RawMaterialLocation.location_code.ilike(keyword),
            RawMaterialLocation.location_name.ilike(keyword),
        )
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)
    total = int(db.execute(count_stmt).scalar_one() or 0)
    rows = db.execute(
        stmt.order_by(RawMaterialLocation.location_code.asc()).limit(size).offset((page - 1) * size)
    ).all()
    items = []
    for location, partner_name, current_qty in rows:
        out = RawMaterialLocationOut.model_validate(location, from_attributes=True)
        out.partner_name = partner_name
        out.current_qty = _q2(Decimal(current_qty or 0))
        items.append(out)
    return RawMaterialLocationListOut(items=items, total=total, page=page, size=size)


def list_raw_material_inventory_lots_for_grid(
    db: Session,
    *,
    raw_material_id: int | None = None,
    location_id: int | None = None,
    q: str | None = None,
    page: int = 1,
    size: int = 100,
) -> RawMaterialInventoryLotListOut:
    stmt = (
        select(RawMaterialInventoryLot, RawMaterial, RawMaterialLocation)
        .join(RawMaterial, RawMaterial.raw_material_id == RawMaterialInventoryLot.raw_material_id)
        .join(
            RawMaterialLocation,
            RawMaterialLocation.raw_material_location_id
            == RawMaterialInventoryLot.raw_material_location_id,
        )
        .where(RawMaterialInventoryLot.current_qty > 0)
    )
    count_stmt = (
        select(func.count())
        .select_from(RawMaterialInventoryLot)
        .join(RawMaterial, RawMaterial.raw_material_id == RawMaterialInventoryLot.raw_material_id)
        .join(
            RawMaterialLocation,
            RawMaterialLocation.raw_material_location_id
            == RawMaterialInventoryLot.raw_material_location_id,
        )
        .where(RawMaterialInventoryLot.current_qty > 0)
    )
    if raw_material_id is not None:
        stmt = stmt.where(RawMaterialInventoryLot.raw_material_id == raw_material_id)
        count_stmt = count_stmt.where(RawMaterialInventoryLot.raw_material_id == raw_material_id)
    if location_id is not None:
        stmt = stmt.where(RawMaterialInventoryLot.raw_material_location_id == location_id)
        count_stmt = count_stmt.where(RawMaterialInventoryLot.raw_material_location_id == location_id)
    if q and q.strip():
        keyword = f"%{q.strip()}%"
        condition = or_(
            RawMaterial.material_code.ilike(keyword),
            RawMaterial.material_name.ilike(keyword),
            RawMaterialInventoryLot.lot_no.ilike(keyword),
            RawMaterialLocation.location_name.ilike(keyword),
        )
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    total = int(db.execute(count_stmt).scalar_one() or 0)
    rows = db.execute(
        stmt.order_by(
            RawMaterial.material_code.asc(),
            RawMaterialLocation.location_code.asc(),
            RawMaterialInventoryLot.lot_no.asc(),
        )
        .limit(size)
        .offset((page - 1) * size)
    ).all()
    items = []
    for lot, material, location in rows:
        items.append(
            RawMaterialInventoryLotOut(
                raw_material_inventory_lot_id=lot.raw_material_inventory_lot_id,
                raw_material_id=lot.raw_material_id,
                raw_material_location_id=lot.raw_material_location_id,
                material_code=material.material_code,
                material_name=material.material_name,
                material_spec=material.material_spec,
                width_mm=material.width_mm,
                uom=material.uom,
                location_code=location.location_code,
                location_name=location.location_name,
                location_type=location.location_type,
                lot_no=lot.lot_no,
                current_qty=_q2(lot.current_qty),
                unit_cost=_q4(lot.unit_cost),
                inventory_amount=_amount(lot.current_qty, lot.unit_cost),
                received_at=lot.received_at,
                updated_at=lot.updated_at,
            )
        )
    return RawMaterialInventoryLotListOut(items=items, total=total, page=page, size=size)


def list_raw_material_movements_for_grid(
    db: Session,
    *,
    raw_material_id: int | None = None,
    location_id: int | None = None,
    inventory_lot_id: int | None = None,
    lot_no: str | None = None,
    movement_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    size: int = 100,
) -> RawMaterialMovementListOut:
    stmt = (
        select(
            RawMaterialInventoryMovement.raw_material_inventory_movement_id,
            RawMaterialInventoryMovement.raw_material_id,
            RawMaterialInventoryMovement.raw_material_location_id,
            RawMaterialInventoryMovement.raw_material_inventory_lot_id,
            RawMaterial.material_code,
            RawMaterial.material_name,
            RawMaterialLocation.location_name,
            RawMaterialInventoryMovement.lot_no,
            RawMaterialInventoryMovement.movement_type,
            RawMaterialInventoryMovement.qty,
            RawMaterialInventoryMovement.balance_after,
            RawMaterialInventoryMovement.unit_cost_snapshot,
            RawMaterialInventoryMovement.amount_snapshot,
            RawMaterialInventoryMovement.source_type,
            RawMaterialInventoryMovement.source_id,
            RawMaterialInventoryMovement.transfer_key,
            RawMaterialInventoryMovement.memo,
            RawMaterialInventoryMovement.created_at,
        )
        .select_from(RawMaterialInventoryMovement)
        .join(RawMaterial, RawMaterial.raw_material_id == RawMaterialInventoryMovement.raw_material_id)
        .join(
            RawMaterialLocation,
            RawMaterialLocation.raw_material_location_id
            == RawMaterialInventoryMovement.raw_material_location_id,
        )
    )
    count_stmt = select(func.count()).select_from(RawMaterialInventoryMovement)
    if raw_material_id is not None:
        stmt = stmt.where(RawMaterialInventoryMovement.raw_material_id == raw_material_id)
        count_stmt = count_stmt.where(RawMaterialInventoryMovement.raw_material_id == raw_material_id)
    if location_id is not None:
        stmt = stmt.where(RawMaterialInventoryMovement.raw_material_location_id == location_id)
        count_stmt = count_stmt.where(RawMaterialInventoryMovement.raw_material_location_id == location_id)
    if inventory_lot_id is not None:
        stmt = stmt.where(RawMaterialInventoryMovement.raw_material_inventory_lot_id == inventory_lot_id)
        count_stmt = count_stmt.where(
            RawMaterialInventoryMovement.raw_material_inventory_lot_id == inventory_lot_id
        )
    if lot_no and lot_no.strip():
        keyword = f"%{lot_no.strip()}%"
        stmt = stmt.where(RawMaterialInventoryMovement.lot_no.ilike(keyword))
        count_stmt = count_stmt.where(RawMaterialInventoryMovement.lot_no.ilike(keyword))
    if movement_type:
        normalized = movement_type.strip().upper()
        stmt = stmt.where(RawMaterialInventoryMovement.movement_type == normalized)
        count_stmt = count_stmt.where(RawMaterialInventoryMovement.movement_type == normalized)
    if date_from is not None:
        from_dt = datetime.combine(date_from, time.min)
        stmt = stmt.where(RawMaterialInventoryMovement.created_at >= from_dt)
        count_stmt = count_stmt.where(RawMaterialInventoryMovement.created_at >= from_dt)
    if date_to is not None:
        to_dt = datetime.combine(date_to, time.max)
        stmt = stmt.where(RawMaterialInventoryMovement.created_at <= to_dt)
        count_stmt = count_stmt.where(RawMaterialInventoryMovement.created_at <= to_dt)

    total = int(db.execute(count_stmt).scalar_one() or 0)
    rows = (
        db.execute(
            stmt.order_by(
                RawMaterialInventoryMovement.created_at.desc(),
                RawMaterialInventoryMovement.raw_material_inventory_movement_id.desc(),
            )
            .limit(size)
            .offset((page - 1) * size)
        )
        .mappings()
        .all()
    )
    return RawMaterialMovementListOut(items=[_movement_out(row) for row in rows], total=total, page=page, size=size)
