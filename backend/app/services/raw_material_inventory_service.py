from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.raw_material import RawMaterial
from app.models.raw_material_inventory import RawMaterialInventory
from app.models.raw_material_inventory_lot import RawMaterialInventoryLot
from app.models.raw_material_inventory_movement import RawMaterialInventoryMovement
from app.models.raw_material_location import RawMaterialLocation
from app.schemas.raw_material import (
    RawMaterialAdjustmentIn,
    RawMaterialInboundIn,
    RawMaterialMovementListOut,
    RawMaterialMovementOut,
    RawMaterialTransferIn,
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


def _normalize_code(value: str) -> str:
    return value.strip().upper()


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _movement_out(row) -> RawMaterialMovementOut:
    return RawMaterialMovementOut(**dict(row))


def _require_material(db: Session, raw_material_id: int, *, active_only: bool = True) -> RawMaterial:
    material = db.get(RawMaterial, raw_material_id)
    if material is None or (active_only and not material.is_active):
        raise HTTPException(status_code=404, detail="Raw material not found")
    return material


def _require_location(db: Session, location_id: int, *, active_only: bool = True) -> RawMaterialLocation:
    location = db.get(RawMaterialLocation, location_id)
    if location is None or (active_only and not location.is_active):
        raise HTTPException(status_code=404, detail="Raw material location not found")
    return location


def _get_or_create_inventory(
    db: Session,
    *,
    raw_material_id: int,
    raw_material_location_id: int,
) -> RawMaterialInventory:
    inventory = (
        db.execute(
            select(RawMaterialInventory)
            .where(
                RawMaterialInventory.raw_material_id == raw_material_id,
                RawMaterialInventory.raw_material_location_id == raw_material_location_id,
            )
            .with_for_update()
        )
        .scalar_one_or_none()
    )
    if inventory is None:
        inventory = RawMaterialInventory(
            raw_material_id=raw_material_id,
            raw_material_location_id=raw_material_location_id,
            current_qty=Decimal("0"),
        )
        db.add(inventory)
        db.flush()
    return inventory


def _get_or_create_lot(
    db: Session,
    *,
    raw_material_id: int,
    raw_material_location_id: int,
    lot_no: str,
    unit_cost: Decimal | None,
    received_at,
) -> RawMaterialInventoryLot:
    inventory_lot = (
        db.execute(
            select(RawMaterialInventoryLot)
            .where(
                RawMaterialInventoryLot.raw_material_id == raw_material_id,
                RawMaterialInventoryLot.raw_material_location_id == raw_material_location_id,
                func.upper(RawMaterialInventoryLot.lot_no) == lot_no.upper(),
            )
            .with_for_update()
        )
        .scalar_one_or_none()
    )
    if inventory_lot is None:
        inventory_lot = RawMaterialInventoryLot(
            raw_material_id=raw_material_id,
            raw_material_location_id=raw_material_location_id,
            lot_no=lot_no,
            current_qty=Decimal("0"),
            unit_cost=unit_cost,
            received_at=received_at,
        )
        db.add(inventory_lot)
        db.flush()
        return inventory_lot

    if unit_cost is not None:
        inventory_lot.unit_cost = unit_cost
    if received_at is not None and inventory_lot.received_at is None:
        inventory_lot.received_at = received_at
    return inventory_lot


def inbound_raw_material_in_session(db: Session, payload: RawMaterialInboundIn) -> RawMaterialMovementOut:
    material = _require_material(db, payload.raw_material_id)
    location = _require_location(db, payload.raw_material_location_id)
    lot_no = _normalize_code(payload.lot_no)
    qty = _q2(payload.qty)
    unit_cost = _q4(payload.unit_cost if payload.unit_cost is not None else material.standard_unit_cost)

    inventory = _get_or_create_inventory(
        db,
        raw_material_id=material.raw_material_id,
        raw_material_location_id=location.raw_material_location_id,
    )
    inventory_lot = _get_or_create_lot(
        db,
        raw_material_id=material.raw_material_id,
        raw_material_location_id=location.raw_material_location_id,
        lot_no=lot_no,
        unit_cost=unit_cost,
        received_at=payload.received_at,
    )
    inventory.current_qty = _q2(inventory.current_qty + qty)
    inventory_lot.current_qty = _q2(inventory_lot.current_qty + qty)
    movement = RawMaterialInventoryMovement(
        raw_material_id=material.raw_material_id,
        raw_material_location_id=location.raw_material_location_id,
        raw_material_inventory_lot_id=inventory_lot.raw_material_inventory_lot_id,
        lot_no=inventory_lot.lot_no,
        movement_type="INBOUND",
        qty=qty,
        balance_after=inventory.current_qty,
        unit_cost_snapshot=unit_cost,
        amount_snapshot=_amount(qty, unit_cost),
        source_type="RAW_MATERIAL_INBOUND",
        memo=_normalize_text(payload.memo),
    )
    db.add(movement)
    db.flush()
    db.refresh(movement)
    return _movement_out(
        {
            "raw_material_inventory_movement_id": movement.raw_material_inventory_movement_id,
            "raw_material_id": movement.raw_material_id,
            "raw_material_location_id": movement.raw_material_location_id,
            "raw_material_inventory_lot_id": movement.raw_material_inventory_lot_id,
            "material_code": material.material_code,
            "material_name": material.material_name,
            "location_name": location.location_name,
            "lot_no": movement.lot_no,
            "movement_type": movement.movement_type,
            "qty": movement.qty,
            "balance_after": movement.balance_after,
            "unit_cost_snapshot": movement.unit_cost_snapshot,
            "amount_snapshot": movement.amount_snapshot,
            "source_type": movement.source_type,
            "source_id": movement.source_id,
            "transfer_key": movement.transfer_key,
            "memo": movement.memo,
            "created_at": movement.created_at,
        }
    )


def transfer_raw_material_in_session(db: Session, payload: RawMaterialTransferIn) -> RawMaterialMovementListOut:
    source_lot = (
        db.execute(
            select(RawMaterialInventoryLot)
            .where(RawMaterialInventoryLot.raw_material_inventory_lot_id == payload.raw_material_inventory_lot_id)
            .with_for_update()
        )
        .scalar_one_or_none()
    )
    if source_lot is None:
        raise HTTPException(status_code=404, detail="Raw material inventory lot not found")
    if source_lot.raw_material_location_id == payload.to_location_id:
        raise HTTPException(status_code=422, detail="Cannot transfer to same location")

    source_location = _require_location(db, source_lot.raw_material_location_id, active_only=False)
    to_location = _require_location(db, payload.to_location_id)
    material = _require_material(db, source_lot.raw_material_id)
    qty = _q2(payload.qty)
    if source_lot.current_qty < qty:
        raise HTTPException(status_code=409, detail="Source lot inventory is insufficient")

    source_inventory = _get_or_create_inventory(
        db,
        raw_material_id=source_lot.raw_material_id,
        raw_material_location_id=source_lot.raw_material_location_id,
    )
    target_inventory = _get_or_create_inventory(
        db,
        raw_material_id=source_lot.raw_material_id,
        raw_material_location_id=payload.to_location_id,
    )
    target_lot = _get_or_create_lot(
        db,
        raw_material_id=source_lot.raw_material_id,
        raw_material_location_id=payload.to_location_id,
        lot_no=source_lot.lot_no,
        unit_cost=source_lot.unit_cost,
        received_at=source_lot.received_at,
    )
    transfer_key = f"RMTR-{uuid4().hex[:16].upper()}"
    source_lot.current_qty = _q2(source_lot.current_qty - qty)
    source_inventory.current_qty = _q2(source_inventory.current_qty - qty)
    target_lot.current_qty = _q2(target_lot.current_qty + qty)
    target_inventory.current_qty = _q2(target_inventory.current_qty + qty)
    memo = _normalize_text(payload.memo)
    out_movement = RawMaterialInventoryMovement(
        raw_material_id=source_lot.raw_material_id,
        raw_material_location_id=source_lot.raw_material_location_id,
        raw_material_inventory_lot_id=source_lot.raw_material_inventory_lot_id,
        lot_no=source_lot.lot_no,
        movement_type="TRANSFER_OUT",
        qty=-qty,
        balance_after=source_inventory.current_qty,
        unit_cost_snapshot=source_lot.unit_cost,
        amount_snapshot=_amount(qty, source_lot.unit_cost),
        source_type="RAW_MATERIAL_TRANSFER",
        transfer_key=transfer_key,
        memo=memo,
    )
    in_movement = RawMaterialInventoryMovement(
        raw_material_id=target_lot.raw_material_id,
        raw_material_location_id=target_lot.raw_material_location_id,
        raw_material_inventory_lot_id=target_lot.raw_material_inventory_lot_id,
        lot_no=target_lot.lot_no,
        movement_type="TRANSFER_IN",
        qty=qty,
        balance_after=target_inventory.current_qty,
        unit_cost_snapshot=target_lot.unit_cost,
        amount_snapshot=_amount(qty, target_lot.unit_cost),
        source_type="RAW_MATERIAL_TRANSFER",
        transfer_key=transfer_key,
        memo=memo,
    )
    db.add_all([out_movement, in_movement])
    db.flush()

    rows = []
    for movement, location_name in (
        (out_movement, source_location.location_name),
        (in_movement, to_location.location_name),
    ):
        db.refresh(movement)
        rows.append(
            {
                "raw_material_inventory_movement_id": movement.raw_material_inventory_movement_id,
                "raw_material_id": movement.raw_material_id,
                "raw_material_location_id": movement.raw_material_location_id,
                "raw_material_inventory_lot_id": movement.raw_material_inventory_lot_id,
                "material_code": material.material_code,
                "material_name": material.material_name,
                "location_name": location_name,
                "lot_no": movement.lot_no,
                "movement_type": movement.movement_type,
                "qty": movement.qty,
                "balance_after": movement.balance_after,
                "unit_cost_snapshot": movement.unit_cost_snapshot,
                "amount_snapshot": movement.amount_snapshot,
                "source_type": movement.source_type,
                "source_id": movement.source_id,
                "transfer_key": movement.transfer_key,
                "memo": movement.memo,
                "created_at": movement.created_at,
            }
        )
    return RawMaterialMovementListOut(items=[_movement_out(row) for row in rows], total=2, page=1, size=2)


def adjust_raw_material_in_session(
    db: Session,
    *,
    payload: RawMaterialAdjustmentIn,
    direction: str,
) -> RawMaterialMovementOut:
    normalized_direction = direction.strip().upper()
    if normalized_direction not in {"IN", "OUT"}:
        raise HTTPException(status_code=422, detail="direction must be IN or OUT")
    inventory_lot = (
        db.execute(
            select(RawMaterialInventoryLot)
            .where(RawMaterialInventoryLot.raw_material_inventory_lot_id == payload.raw_material_inventory_lot_id)
            .with_for_update()
        )
        .scalar_one_or_none()
    )
    if inventory_lot is None:
        raise HTTPException(status_code=404, detail="Raw material inventory lot not found")
    material = _require_material(db, inventory_lot.raw_material_id, active_only=False)
    location = _require_location(db, inventory_lot.raw_material_location_id, active_only=False)
    inventory = _get_or_create_inventory(
        db,
        raw_material_id=inventory_lot.raw_material_id,
        raw_material_location_id=inventory_lot.raw_material_location_id,
    )
    qty = _q2(payload.qty)
    if normalized_direction == "OUT":
        if inventory_lot.current_qty < qty or inventory.current_qty < qty:
            raise HTTPException(status_code=409, detail="Inventory is insufficient")
        movement_qty = -qty
        inventory_lot.current_qty = _q2(inventory_lot.current_qty - qty)
        inventory.current_qty = _q2(inventory.current_qty - qty)
        movement_type = "ADJUST_OUT"
    else:
        movement_qty = qty
        inventory_lot.current_qty = _q2(inventory_lot.current_qty + qty)
        inventory.current_qty = _q2(inventory.current_qty + qty)
        movement_type = "ADJUST_IN"
    movement = RawMaterialInventoryMovement(
        raw_material_id=inventory_lot.raw_material_id,
        raw_material_location_id=inventory_lot.raw_material_location_id,
        raw_material_inventory_lot_id=inventory_lot.raw_material_inventory_lot_id,
        lot_no=inventory_lot.lot_no,
        movement_type=movement_type,
        qty=movement_qty,
        balance_after=inventory.current_qty,
        unit_cost_snapshot=inventory_lot.unit_cost,
        amount_snapshot=_amount(qty, inventory_lot.unit_cost),
        source_type="RAW_MATERIAL_ADJUST",
        memo=_normalize_text(payload.memo),
    )
    db.add(movement)
    db.flush()
    db.refresh(movement)
    return _movement_out(
        {
            "raw_material_inventory_movement_id": movement.raw_material_inventory_movement_id,
            "raw_material_id": movement.raw_material_id,
            "raw_material_location_id": movement.raw_material_location_id,
            "raw_material_inventory_lot_id": movement.raw_material_inventory_lot_id,
            "material_code": material.material_code,
            "material_name": material.material_name,
            "location_name": location.location_name,
            "lot_no": movement.lot_no,
            "movement_type": movement.movement_type,
            "qty": movement.qty,
            "balance_after": movement.balance_after,
            "unit_cost_snapshot": movement.unit_cost_snapshot,
            "amount_snapshot": movement.amount_snapshot,
            "source_type": movement.source_type,
            "source_id": movement.source_id,
            "transfer_key": movement.transfer_key,
            "memo": movement.memo,
            "created_at": movement.created_at,
        }
    )
