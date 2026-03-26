from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.lot import lot_crud
from app.db.session import get_db
from app.models.lot import Lot
from app.models.lot_step import LotStep
from app.models.order_line import OrderLine
from app.models.partner import Partner
from app.models.process import Process
from app.models.product import Product
from app.models.routing_template_step import RoutingTemplateStep
from app.schemas.lot import LotCreate, LotOut, LotDetailOut, LotListOut, PageMeta

router = APIRouter(prefix="/lots", tags=["Lot"])


def _generate_lot_no(db: Session, created_date: date, e_fixed: str = "0") -> str:
    yy = f"{created_date.year % 100:02d}"
    mm = f"{created_date.month:02d}"
    dd = f"{created_date.day:02d}"
    prefix = f"CT{yy}{mm}{dd}{e_fixed}"

    last = db.execute(
        select(Lot.lot_no)
        .where(Lot.lot_no.like(f"{prefix}%"))
        .order_by(desc(Lot.lot_no))
        .limit(1)
    ).scalar_one_or_none()

    if not last:
        nn = 1
    else:
        try:
            nn = int(last[-2:]) + 1
        except ValueError:
            nn = 1

    if nn > 99:
        raise HTTPException(status_code=409, detail="LOT sequence exceeded for the day (NN > 99)")

    return f"{prefix}{nn:02d}"


def _ensure_order_line(db: Session, order_line_id: int) -> OrderLine:
    ol = db.get(OrderLine, order_line_id)
    if not ol or not ol.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found or inactive")
    return ol


def _ensure_parent_lot(db: Session, parent_lot_id: int) -> Lot:
    parent = db.get(Lot, parent_lot_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent LOT not found")
    return parent


def _create_lot_steps_from_routing(db: Session, lot_id: int, routing_template_id: int) -> None:
    steps = db.execute(
        select(RoutingTemplateStep)
        .where(
            RoutingTemplateStep.routing_template_id == routing_template_id,
            RoutingTemplateStep.is_active == True,  # noqa: E712
        )
        .order_by(RoutingTemplateStep.step_seq.asc())
    ).scalars().all()

    if not steps:
        raise HTTPException(status_code=409, detail="RoutingTemplate has no active steps")

    process_ids = [s.process_id for s in steps]
    procs = db.execute(select(Process).where(Process.process_id.in_(process_ids))).scalars().all()
    process_map = {p.process_id: p for p in procs}

    for s in steps:
        p = process_map.get(s.process_id)
        if not p:
            raise HTTPException(status_code=409, detail=f"Process not found for process_id={s.process_id}")

        db.add(
            LotStep(
                lot_id=lot_id,
                step_seq=s.step_seq,
                process_id=s.process_id,
                process_code=p.process_code,
                process_name=p.process_name,
                process_type=s.default_process_type,
                status="WAITING",
            )
        )


def _normalize_optional_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _validate_material_fields(payload: LotCreate):
    material_lot_no = _normalize_optional_str(payload.material_lot_no)
    material_used_qty = payload.material_used_qty
    material_sheet_count = payload.material_sheet_count

    has_lot_no = material_lot_no is not None
    has_used_qty = material_used_qty is not None
    has_sheet_count = material_sheet_count is not None

    if has_lot_no and not has_used_qty:
        raise HTTPException(status_code=409, detail="material_used_qty is required when material_lot_no is provided")

    if has_used_qty and not has_lot_no:
        raise HTTPException(status_code=409, detail="material_lot_no is required when material_used_qty is provided")

    if has_sheet_count and not has_lot_no:
        raise HTTPException(status_code=409, detail="material_lot_no is required when material_sheet_count is provided")

    return material_lot_no, material_used_qty, material_sheet_count


@router.post("", response_model=LotDetailOut, status_code=http_status.HTTP_201_CREATED)
def create_lot(payload: LotCreate, db: Session = Depends(get_db)):
    ol = _ensure_order_line(db, payload.order_line_id)

    product = db.get(Product, ol.product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=409, detail="Product not found or inactive")

    created_date = payload.created_date or date.today()
    parent_lot_id_in = payload.parent_lot_id or None
    is_rework = parent_lot_id_in is not None
    lot_qty = int(payload.lot_qty)

    material_lot_no, material_used_qty, material_sheet_count = _validate_material_fields(payload)

    parent_lot_id = None

    if not is_rework and ol.status != "OPEN":
        raise HTTPException(status_code=409, detail="Primary LOT can only be created when OrderLine is OPEN")

    if is_rework:
        parent = _ensure_parent_lot(db, parent_lot_id_in)

        if parent.order_line_id != ol.order_line_id:
            raise HTTPException(status_code=409, detail="Parent LOT must belong to same OrderLine")

        if parent.parent_lot_id is not None:
            raise HTTPException(status_code=409, detail="Parent LOT must be a primary LOT")

        if parent.status not in ("DONE", "CANCELED"):
            raise HTTPException(
                status_code=409,
                detail="Rework LOT can only be created when parent LOT is DONE or CANCELED",
            )

        parent_lot_id = parent.lot_id

        if ol.status == "DONE":
            ol.status = "CLOSED"

    for _ in range(3):
        lot_no = _generate_lot_no(db, created_date, e_fixed="0")

        lot = Lot(
            lot_no=lot_no,
            order_line_id=ol.order_line_id,
            product_id=ol.product_id,
            parent_lot_id=parent_lot_id,
            lot_qty=lot_qty,
            uom=ol.uom,
            material_lot_no=material_lot_no,
            material_used_qty=material_used_qty,
            material_sheet_count=material_sheet_count,
            created_date=created_date,
            due_date=ol.due_date,
            memo=payload.memo,
            status="WAITING",
        )

        try:
            lot_crud.create(db, lot)
            _create_lot_steps_from_routing(db, lot.lot_id, product.routing_template_id)

            if not is_rework and ol.status == "OPEN":
                ol.status = "CLOSED"

            db.commit()
            db.refresh(lot)
            break

        except IntegrityError:
            db.rollback()
            continue
    else:
        raise HTTPException(status_code=409, detail="Failed to generate unique lot_no (retry exceeded)")

    out = LotDetailOut.model_validate(lot, from_attributes=True)

    partner = db.get(Partner, ol.partner_id)
    out.order_no = ol.order_no
    out.line_no = ol.line_no
    out.partner_id = ol.partner_id
    out.partner_name = partner.name if partner else None
    out.product_code = product.product_code
    out.product_name = product.product_name
    out.steps = [s for s in lot.steps]

    return out


@router.get("", response_model=LotListOut)
def list_lots(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    order_line_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    partner_id: Optional[int] = Query(None),
    due_date_from: Optional[date] = Query(None),
    due_date_to: Optional[date] = Query(None),
    created_date_from: Optional[date] = Query(None),
    created_date_to: Optional[date] = Query(None),
    inspection_schedule_registered: Optional[bool] = Query(None),
):
    items, total = lot_crud.list_with_joins(
        db,
        page=page,
        size=size,
        status=status,
        q=q,
        order_line_id=order_line_id,
        product_id=product_id,
        partner_id=partner_id,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        created_date_from=created_date_from,
        created_date_to=created_date_to,
        inspection_schedule_registered=inspection_schedule_registered,
    )

    return LotListOut(
        items=[LotOut(**x) for x in items],
        meta=PageMeta(page=page, size=size, total=total),
    )


@router.get("/{lot_id}", response_model=LotDetailOut)
def get_lot(lot_id: int, db: Session = Depends(get_db)):
    lot = lot_crud.get(db, lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="LOT not found")

    ol = db.get(OrderLine, lot.order_line_id)
    product = db.get(Product, lot.product_id)
    partner = db.get(Partner, ol.partner_id) if ol else None

    out = LotDetailOut.model_validate(lot, from_attributes=True)

    if ol:
        out.order_no = ol.order_no
        out.line_no = ol.line_no
        out.partner_id = ol.partner_id
        out.partner_name = partner.name if partner else None

    if product:
        out.product_code = product.product_code
        out.product_name = product.product_name

    out.steps = [s for s in lot.steps]
    return out