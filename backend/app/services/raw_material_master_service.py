from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.partner import Partner
from app.models.raw_material import RawMaterial
from app.models.raw_material_inventory import RawMaterialInventory
from app.models.raw_material_location import RawMaterialLocation
from app.schemas.raw_material import (
    RawMaterialCreate,
    RawMaterialLocationCreate,
    RawMaterialLocationOut,
    RawMaterialLocationUpdate,
    RawMaterialOut,
    RawMaterialUpdate,
)

LOCATION_TYPES = {"INTERNAL_WAREHOUSE", "OUTSOURCE_VENDOR", "OTHER"}
LOCATION_CODE_PREFIX = "RMLOC-"


def _q4(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


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


def _require_active_partner(db: Session, partner_id: int) -> Partner:
    partner = db.get(Partner, partner_id)
    if partner is None or not partner.is_active:
        raise HTTPException(status_code=404, detail="Partner not found")
    return partner


def create_raw_material_in_session(db: Session, payload: RawMaterialCreate) -> RawMaterialOut:
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
    db.flush()
    db.refresh(material)
    return RawMaterialOut.model_validate(material, from_attributes=True)


def update_raw_material_in_session(
    db: Session,
    *,
    raw_material_id: int,
    payload: RawMaterialUpdate,
) -> RawMaterialOut:
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
    db.flush()
    db.refresh(material)
    return RawMaterialOut.model_validate(material, from_attributes=True)


def deactivate_raw_material_in_session(db: Session, raw_material_id: int) -> RawMaterialOut:
    material = _require_material(db, raw_material_id, active_only=False)
    current_qty = db.execute(
        select(func.coalesce(func.sum(RawMaterialInventory.current_qty), 0)).where(
            RawMaterialInventory.raw_material_id == raw_material_id
        )
    ).scalar_one()
    if Decimal(current_qty or 0) != 0:
        raise HTTPException(status_code=409, detail="Cannot deactivate raw material with inventory")
    material.is_active = False
    db.flush()
    db.refresh(material)
    return RawMaterialOut.model_validate(material, from_attributes=True)


def create_raw_material_location_in_session(
    db: Session,
    payload: RawMaterialLocationCreate,
) -> RawMaterialLocationOut:
    location_type = _validate_location_type(payload.location_type)
    if payload.partner_id is not None:
        _require_active_partner(db, payload.partner_id)
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
    db.flush()
    db.refresh(location)
    return RawMaterialLocationOut.model_validate(location, from_attributes=True)


def update_raw_material_location_in_session(
    db: Session,
    *,
    location_id: int,
    payload: RawMaterialLocationUpdate,
) -> RawMaterialLocationOut:
    location = _require_location(db, location_id, active_only=False)
    if payload.location_name is not None:
        location.location_name = payload.location_name.strip()
    if payload.location_type is not None:
        location.location_type = _validate_location_type(payload.location_type)
    if "partner_id" in payload.model_fields_set:
        if payload.partner_id is None:
            location.partner_id = None
        else:
            _require_active_partner(db, payload.partner_id)
            location.partner_id = payload.partner_id
    if payload.is_active is not None:
        location.is_active = payload.is_active
    if payload.memo is not None:
        location.memo = _normalize_text(payload.memo)
    db.flush()
    db.refresh(location)
    return RawMaterialLocationOut.model_validate(location, from_attributes=True)


def deactivate_raw_material_location_in_session(db: Session, location_id: int) -> RawMaterialLocationOut:
    location = _require_location(db, location_id, active_only=False)
    current_qty = db.execute(
        select(func.coalesce(func.sum(RawMaterialInventory.current_qty), 0)).where(
            RawMaterialInventory.raw_material_location_id == location_id
        )
    ).scalar_one()
    if Decimal(current_qty or 0) != 0:
        raise HTTPException(status_code=409, detail="Cannot deactivate location with inventory")
    location.is_active = False
    db.flush()
    db.refresh(location)
    return RawMaterialLocationOut.model_validate(location, from_attributes=True)
