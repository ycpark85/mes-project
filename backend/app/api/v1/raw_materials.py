from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.partner import Partner
from app.models.raw_material import RawMaterial
from app.models.raw_material_inventory import RawMaterialInventory
from app.models.raw_material_inventory_lot import RawMaterialInventoryLot
from app.models.raw_material_inventory_movement import RawMaterialInventoryMovement
from app.models.raw_material_location import RawMaterialLocation
from app.schemas.raw_material import (
    RawMaterialAdjustmentIn,
    RawMaterialCreate,
    RawMaterialInboundIn,
    RawMaterialInventoryLotListOut,
    RawMaterialInventoryLotOut,
    RawMaterialListOut,
    RawMaterialLocationCreate,
    RawMaterialLocationListOut,
    RawMaterialLocationOut,
    RawMaterialLocationUpdate,
    RawMaterialMovementListOut,
    RawMaterialMovementOut,
    RawMaterialOut,
    RawMaterialTransferIn,
    RawMaterialUpdate,
)

router = APIRouter(prefix="/raw-materials", tags=["RawMaterial"])

LOCATION_TYPES = {"INTERNAL_WAREHOUSE", "OUTSOURCE_VENDOR", "OTHER"}
LOCATION_CODE_PREFIX = "RMLOC-"


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


def _generate_location_code() -> str:
    return f"{LOCATION_CODE_PREFIX}{uuid4().hex[:8].upper()}"


def _validate_location_type(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in LOCATION_TYPES:
        raise HTTPException(status_code=422, detail="Invalid location_type")
    return normalized


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


def _movement_out(row) -> RawMaterialMovementOut:
    data = dict(row)
    return RawMaterialMovementOut(**data)


@router.post("", response_model=RawMaterialOut, status_code=status.HTTP_201_CREATED)
def create_raw_material(payload: RawMaterialCreate, db: Session = Depends(get_db)):
    material = RawMaterial(
        material_code=_normalize_code(payload.material_code),
        material_name=payload.material_name.strip(),
        material_spec=_normalize_text(payload.material_spec),
        width_mm=payload.width_mm,
        material_type=_normalize_text(payload.material_type),
        uom=payload.uom.strip().upper(),
        standard_unit_cost=_q4(payload.standard_unit_cost),
        is_active=payload.is_active,
        memo=_normalize_text(payload.memo),
    )
    db.add(material)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="material_code already exists")
    db.refresh(material)
    return RawMaterialOut.model_validate(material, from_attributes=True)


@router.get("", response_model=RawMaterialListOut)
def list_raw_materials(
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    q: str | None = Query(None),
    is_active: bool | None = Query(True),
    db: Session = Depends(get_db),
):
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


@router.patch("/{raw_material_id}", response_model=RawMaterialOut)
def update_raw_material(raw_material_id: int, payload: RawMaterialUpdate, db: Session = Depends(get_db)):
    material = _require_material(db, raw_material_id, active_only=False)
    if payload.material_name is not None:
        material.material_name = payload.material_name.strip()
    if payload.material_spec is not None:
        material.material_spec = _normalize_text(payload.material_spec)
    if payload.width_mm is not None:
        material.width_mm = payload.width_mm
    if payload.material_type is not None:
        material.material_type = _normalize_text(payload.material_type)
    if payload.uom is not None:
        material.uom = payload.uom.strip().upper()
    if payload.standard_unit_cost is not None:
        material.standard_unit_cost = _q4(payload.standard_unit_cost)
    if payload.is_active is not None:
        material.is_active = payload.is_active
    if payload.memo is not None:
        material.memo = _normalize_text(payload.memo)
    db.commit()
    db.refresh(material)
    return RawMaterialOut.model_validate(material, from_attributes=True)


@router.delete("/{raw_material_id}", response_model=RawMaterialOut)
def delete_raw_material(raw_material_id: int, db: Session = Depends(get_db)):
    material = _require_material(db, raw_material_id, active_only=False)
    current_qty = db.execute(
        select(func.coalesce(func.sum(RawMaterialInventory.current_qty), 0)).where(
            RawMaterialInventory.raw_material_id == raw_material_id
        )
    ).scalar_one()
    if Decimal(current_qty or 0) != 0:
        raise HTTPException(status_code=409, detail="Cannot deactivate raw material with inventory")
    material.is_active = False
    db.commit()
    db.refresh(material)
    return RawMaterialOut.model_validate(material, from_attributes=True)


@router.post("/locations", response_model=RawMaterialLocationOut, status_code=status.HTTP_201_CREATED)
def create_location(payload: RawMaterialLocationCreate, db: Session = Depends(get_db)):
    location_type = _validate_location_type(payload.location_type)
    if payload.partner_id is not None:
        partner = db.get(Partner, payload.partner_id)
        if partner is None or not partner.is_active:
            raise HTTPException(status_code=404, detail="Partner not found")
    location_code = _normalize_text(payload.location_code)
    location = RawMaterialLocation(
        location_code=_normalize_code(location_code) if location_code else _generate_location_code(),
        location_name=payload.location_name.strip(),
        location_type=location_type,
        partner_id=payload.partner_id,
        is_active=payload.is_active,
        memo=_normalize_text(payload.memo),
    )
    db.add(location)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="location_code already exists")
    db.refresh(location)
    return RawMaterialLocationOut.model_validate(location, from_attributes=True)


@router.get("/locations", response_model=RawMaterialLocationListOut)
def list_locations(
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    q: str | None = Query(None),
    is_active: bool | None = Query(True),
    db: Session = Depends(get_db),
):
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
        .outerjoin(current_qty_sq, current_qty_sq.c.raw_material_location_id == RawMaterialLocation.raw_material_location_id)
    )
    count_stmt = select(func.count()).select_from(RawMaterialLocation)
    if is_active is not None:
        stmt = stmt.where(RawMaterialLocation.is_active == is_active)
        count_stmt = count_stmt.where(RawMaterialLocation.is_active == is_active)
    if q and q.strip():
        keyword = f"%{q.strip()}%"
        condition = or_(RawMaterialLocation.location_code.ilike(keyword), RawMaterialLocation.location_name.ilike(keyword))
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


@router.patch("/locations/{location_id}", response_model=RawMaterialLocationOut)
def update_location(location_id: int, payload: RawMaterialLocationUpdate, db: Session = Depends(get_db)):
    location = _require_location(db, location_id, active_only=False)
    if payload.location_name is not None:
        location.location_name = payload.location_name.strip()
    if payload.location_type is not None:
        location.location_type = _validate_location_type(payload.location_type)
    if "partner_id" in payload.model_fields_set:
        if payload.partner_id is None:
            location.partner_id = None
        else:
            partner = db.get(Partner, payload.partner_id)
            if partner is None or not partner.is_active:
                raise HTTPException(status_code=404, detail="Partner not found")
            location.partner_id = payload.partner_id
    if payload.is_active is not None:
        location.is_active = payload.is_active
    if payload.memo is not None:
        location.memo = _normalize_text(payload.memo)
    db.commit()
    db.refresh(location)
    return RawMaterialLocationOut.model_validate(location, from_attributes=True)


@router.delete("/locations/{location_id}", response_model=RawMaterialLocationOut)
def delete_location(location_id: int, db: Session = Depends(get_db)):
    location = _require_location(db, location_id, active_only=False)
    current_qty = db.execute(
        select(func.coalesce(func.sum(RawMaterialInventory.current_qty), 0)).where(
            RawMaterialInventory.raw_material_location_id == location_id
        )
    ).scalar_one()
    if Decimal(current_qty or 0) != 0:
        raise HTTPException(status_code=409, detail="Cannot deactivate location with inventory")
    location.is_active = False
    db.commit()
    db.refresh(location)
    return RawMaterialLocationOut.model_validate(location, from_attributes=True)


@router.get("/inventory-lots", response_model=RawMaterialInventoryLotListOut)
def list_inventory_lots(
    raw_material_id: int | None = Query(None, ge=1),
    location_id: int | None = Query(None, ge=1),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    stmt = (
        select(RawMaterialInventoryLot, RawMaterial, RawMaterialLocation)
        .join(RawMaterial, RawMaterial.raw_material_id == RawMaterialInventoryLot.raw_material_id)
        .join(RawMaterialLocation, RawMaterialLocation.raw_material_location_id == RawMaterialInventoryLot.raw_material_location_id)
        .where(RawMaterialInventoryLot.current_qty > 0)
    )
    count_stmt = (
        select(func.count())
        .select_from(RawMaterialInventoryLot)
        .join(RawMaterial, RawMaterial.raw_material_id == RawMaterialInventoryLot.raw_material_id)
        .join(RawMaterialLocation, RawMaterialLocation.raw_material_location_id == RawMaterialInventoryLot.raw_material_location_id)
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
        inventory_amount = _amount(lot.current_qty, lot.unit_cost)
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
                inventory_amount=inventory_amount,
                received_at=lot.received_at,
                updated_at=lot.updated_at,
            )
        )
    return RawMaterialInventoryLotListOut(items=items, total=total, page=page, size=size)


@router.get("/movements", response_model=RawMaterialMovementListOut)
def list_movements(
    raw_material_id: int | None = Query(None, ge=1),
    location_id: int | None = Query(None, ge=1),
    inventory_lot_id: int | None = Query(None, ge=1),
    lot_no: str | None = Query(None),
    movement_type: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
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
        .join(RawMaterialLocation, RawMaterialLocation.raw_material_location_id == RawMaterialInventoryMovement.raw_material_location_id)
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
        count_stmt = count_stmt.where(RawMaterialInventoryMovement.raw_material_inventory_lot_id == inventory_lot_id)
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


@router.post("/inbound", response_model=RawMaterialMovementOut, status_code=status.HTTP_201_CREATED)
def inbound_raw_material(payload: RawMaterialInboundIn, db: Session = Depends(get_db)):
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
    db.commit()
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


@router.post("/transfer", response_model=RawMaterialMovementListOut, status_code=status.HTTP_201_CREATED)
def transfer_raw_material(payload: RawMaterialTransferIn, db: Session = Depends(get_db)):
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
    db.commit()
    rows = []
    for movement, location_name in ((out_movement, source_lot.location.location_name), (in_movement, to_location.location_name)):
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


@router.post("/adjust", response_model=RawMaterialMovementOut, status_code=status.HTTP_201_CREATED)
def adjust_raw_material(
    payload: RawMaterialAdjustmentIn,
    direction: str = Query(...),
    db: Session = Depends(get_db),
):
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
    db.commit()
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
