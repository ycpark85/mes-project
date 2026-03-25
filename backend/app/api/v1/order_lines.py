# app/api/v1/order_lines.py
from __future__ import annotations

from datetime import date,datetime, timezone
from typing import Optional
from app.models.drawing import Drawing
from app.models.drawing_revision import DrawingRevision
from app.models.drawing_rivision_file import DrawingRevisionFile

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db  # 너희 프로젝트의 get_db 경로에 맞춰 수정
from app.models.order_line import OrderLine
from app.models.partner import Partner
from app.models.product import Product
from app.schemas.order_line import (
    OrderLineCreate,
    OrderLineUpdate,
    OrderLineOut,
    OrderLineListOut,
    PageMeta,
    OrderLineStatus,
)
from app.schemas.order_line_detail import (
    OrderLineDetailDto,
    OrderLineDetailLotDto,
    OrderLineTimelineItemDto,
    OrderLineDetailUpdate,
)
from app.schemas.lot_create_context import (
    LotCreateContextDto,
    LotCreateDrawingDto,
    LotCreatePrimaryCandidateDto,
)
from app.crud.order_line import order_line_crud

from sqlalchemy import update, select, exists, and_
from app.models.lot import Lot
from app.models.lot_step import LotStep

router = APIRouter(prefix="/order-lines", tags=["OrderLine"])


def _ensure_partner_active(db: Session, partner_id: int) -> Partner:
    partner = db.get(Partner, partner_id)
    if not partner or not partner.is_active:
        raise HTTPException(status_code=404, detail="Partner not found or inactive")
    return partner


def _ensure_product_active(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found or inactive")
    return product


@router.post("", response_model=OrderLineOut, status_code=http_status.HTTP_201_CREATED)
def create_order_line(payload: OrderLineCreate, db: Session = Depends(get_db)):
    # FK validate
    _ensure_partner_active(db, payload.partner_id)
    product = _ensure_product_active(db, payload.product_id)

    # uom 스냅샷: 입력값을 신뢰하지 않고 product.uom으로 강제(권장)
    data = payload.model_dump()
    data["uom"] = product.uom

    obj = OrderLine(**data)
    # status/is_active/priority는 모델 default 사용(OPEN/true/0)

    try:
        order_line_crud.create(db, obj)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate order_no+line_no or integrity error")

    # join 표시 필드까지 내려주려면 list_with_search 방식이지만, 단건은 간단히 포함 필드 없이 반환
    # (원하면 여기서 partner/product join해서 partner_name/product_name 넣어줄 수 있음)
    return OrderLineOut.model_validate(obj, from_attributes=True)


@router.get("", response_model=OrderLineListOut)
def list_order_lines(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(True),
    partner_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    order_date_from: Optional[date] = Query(None),
    order_date_to: Optional[date] = Query(None),
    due_date_from: Optional[date] = Query(None),
    due_date_to: Optional[date] = Query(None),
):
    items, total = order_line_crud.list_with_search(
        db,
        page=page,
        size=size,
        q=q,
        status=status if status else None,
        is_active=is_active,
        partner_id=partner_id,
        product_id=product_id,
        order_date_from=order_date_from,
        order_date_to=order_date_to,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
    )

    return OrderLineListOut(
        items=[OrderLineOut(**x) for x in items],
        meta=PageMeta(page=page, size=size, total=total),
    )




@router.patch("/{order_line_id}", response_model=OrderLineOut)
def update_order_line(order_line_id: int, payload: OrderLineUpdate, db: Session = Depends(get_db)):
    obj = order_line_crud.get(db, order_line_id)
    if not obj or not obj.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    data = payload.model_dump(exclude_unset=True)

    # ✅ CLOSED에서 due_date 변경을 허용하기 위해, 먼저 요청된 due_date를 따로 보관
    requested_due_date = data.get("due_date")

    # 상태 기반 수정 제한
    if obj.status == OrderLineStatus.OPEN.value:
        # OPEN: 기존 정책 그대로 (모든 필드 수정 가능 범위는 data에 들어온 것 기준)
        pass

    elif obj.status == OrderLineStatus.CLOSED.value:
        # ✅ CLOSED: due_date + memo/customer_po만 허용
        allow_keys = {"due_date", "memo", "customer_po"}
        forbidden = set(data.keys()) - allow_keys
        if forbidden:
            raise HTTPException(
                status_code=409,
                detail="CLOSED OrderLine can only modify due_date/memo/customer_po",
            )
        data = {k: v for k, v in data.items() if k in allow_keys}

    else:
        # DONE/CANCELED: memo/customer_po만 허용(기존 정책 유지)
        forbidden_keys = {
            "order_no", "line_no",
            "partner_id", "product_id",
            "order_date", "due_date",
            "order_qty", "uom",
            "priority",
        }
        if any(k in data for k in forbidden_keys):
            raise HTTPException(status_code=409, detail="Only OPEN OrderLine can be modified (except memo/customer_po)")

        allow_keys = {"memo", "customer_po"}
        data = {k: v for k, v in data.items() if k in allow_keys}
    old_due_date = obj.due_date
    # FK validate if changed (OPEN에서만 도달)
    if "partner_id" in data:
        _ensure_partner_active(db, data["partner_id"])
    if "product_id" in data:
        product = _ensure_product_active(db, data["product_id"])
        data["uom"] = product.uom
   
    try:
        order_line_crud.update(db, obj, data)

        # ✅ due_date가 실제로 변경되면 "미시작 LOT만" 동기화
        if requested_due_date is not None and requested_due_date != old_due_date:
            # 주의: 위 update로 obj.due_date가 이미 바뀌었을 수 있으니,
            # rowcount 기준으로 동기화는 "payload 값"으로 수행
            _sync_lot_due_date_for_not_started(db, order_line_id, requested_due_date)

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate order_no+line_no or integrity error")

    # 표시 필드 포함해서 반환
    partner = db.get(Partner, obj.partner_id)
    product = db.get(Product, obj.product_id)
    out = OrderLineOut.model_validate(obj, from_attributes=True)
    out.partner_name = partner.name if partner else None
    out.product_code = product.product_code if product else None
    out.product_name = product.product_name if product else None
    return out

@router.delete("/{order_line_id}", response_model=OrderLineOut)
def delete_order_line(order_line_id: int, db: Session = Depends(get_db)):
    obj = order_line_crud.get(db, order_line_id)
    if not obj or not obj.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    # MVP 안전장치: OPEN일 때만 삭제 허용(권장)
    if obj.status != OrderLineStatus.OPEN.value:
        raise HTTPException(status_code=409, detail="Only OPEN OrderLine can be deleted")

    order_line_crud.soft_delete(db, obj)
    db.commit()

    out = OrderLineOut.model_validate(obj, from_attributes=True)
    return out



@router.get("/{order_line_id}/detail", response_model=OrderLineDetailDto)
def get_order_line_detail(order_line_id: int, db: Session = Depends(get_db)):
    order_line = order_line_crud.get(db, order_line_id)
    if not order_line or not order_line.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    partner = db.get(Partner, order_line.partner_id)
    product = db.get(Product, order_line.product_id)

    lots = (
        db.execute(
            select(Lot)
            .options(selectinload(Lot.steps))
            .where(Lot.order_line_id == order_line_id)
            .order_by(Lot.created_date.asc(), Lot.lot_id.asc())
        )
        .scalars()
        .all()
    )

    has_any_lot = len(lots) > 0
    has_base_lot = any(l.parent_lot_id is None for l in lots)

    can_edit = order_line.status in {
        OrderLineStatus.OPEN.value,
        OrderLineStatus.CLOSED.value,
    }
    can_save = can_edit

    # 수주취소 가능:
    # - 연결 LOT가 없거나
    # - 연결 LOT가 전부 CANCELED
    # - 그리고 수주 자체가 DONE/CANCELED가 아니어야 함
    can_cancel_order = (
        order_line.status not in {OrderLineStatus.DONE.value, OrderLineStatus.CANCELED.value}
        and (
            not has_any_lot
            or all(l.status == "CANCELED" for l in lots)
        )
    )

    # 기본 LOT 생성 가능:
    # - 수주 상태 OPEN
    # - 아직 기본 LOT 없음
    can_create_base_lot = (
        order_line.status == OrderLineStatus.OPEN.value
        and not has_base_lot
    )

    lot_items: list[OrderLineDetailLotDto] = []
    for lot in lots:
        is_done_or_canceled = lot.status in {"DONE", "CANCELED"}

        lot_items.append(
            OrderLineDetailLotDto(
                lot_id=lot.lot_id,
                lot_no=lot.lot_no,
                lot_type="REWORK" if lot.parent_lot_id else "NORMAL",
                parent_lot_id=lot.parent_lot_id,
                lot_qty=lot.lot_qty,
                status=lot.status,
                current_process_name=_get_lot_current_process_name(lot),
                is_editable=not is_done_or_canceled,
                can_cancel=not is_done_or_canceled,
                can_create_rework=is_done_or_canceled,
            )
        )

    timeline = _build_detail_timeline(order_line, lots)

    return OrderLineDetailDto(
        order_line_id=order_line.order_line_id,
        order_no=order_line.order_no,
        line_no=order_line.line_no,
        partner_id=order_line.partner_id,
        partner_name=partner.name if partner else "",
        product_id=order_line.product_id,
        product_code=product.product_code if product else "",
        product_name=product.product_name if product else "",
        order_date=order_line.order_date,
        due_date=order_line.due_date,
        order_qty=order_line.order_qty,
        uom=order_line.uom,
        customer_po=order_line.customer_po,
        memo=order_line.memo,
        status=order_line.status,
        status_display=_to_status_display(order_line.status),
        is_active=order_line.is_active,
        can_edit=can_edit,
        can_save=can_save,
        can_cancel_order=can_cancel_order,
        can_create_base_lot=can_create_base_lot,
        lots=lot_items,
        timeline=timeline,
    )

@router.get("/{order_line_id}/lot-create-context", response_model=LotCreateContextDto)
def get_lot_create_context(order_line_id: int, db: Session = Depends(get_db)):
    order_line = order_line_crud.get(db, order_line_id)
    if not order_line or not order_line.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    partner = db.get(Partner, order_line.partner_id)
    product = db.get(Product, order_line.product_id)

    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found or inactive")

    drawing = db.get(Drawing, product.drawing_id) if product.drawing_id else None
    current_revision = None

    if drawing and drawing.current_revision_id:
        current_revision = db.get(DrawingRevision, drawing.current_revision_id)

    drawing_file = None
    original_file = None
    plate_file = None

    if current_revision:
        revision_files = (
            db.execute(
                select(DrawingRevisionFile).where(
                    DrawingRevisionFile.revision_id == current_revision.revision_id
                )
            )
            .scalars()
            .all()
        )

        for f in revision_files:
            kind = (f.file_kind or "").strip().upper()

            if kind == "DRAWING" and drawing_file is None:
                drawing_file = f
            elif kind == "ORIGINAL" and original_file is None:
                original_file = f
            elif kind == "PLATE" and plate_file is None:
                plate_file = f    

    primary_lots = (
        db.execute(
            select(Lot)
            .where(
                Lot.order_line_id == order_line_id,
                Lot.parent_lot_id.is_(None),
            )
            .order_by(Lot.created_date.asc(), Lot.lot_id.asc())
        )
        .scalars()
        .all()
    )

    primary_lot_candidates = [
        LotCreatePrimaryCandidateDto(
            lot_id=lot.lot_id,
            lot_no=lot.lot_no,
            lot_qty=lot.lot_qty,
            uom=lot.uom,
            status=lot.status,
            memo=lot.memo,
            can_create_rework=lot.status in ("DONE", "CANCELED"),
        )
        for lot in primary_lots
    ]

    drawing_dto = LotCreateDrawingDto(
        drawing_id=drawing.drawing_id if drawing else None,
        drawing_no=drawing.drawing_no if drawing else None,
        current_revision_id=current_revision.revision_id if current_revision else None,
        current_revision_no=current_revision.rev_no if current_revision else None,

        drawing_file_id=drawing_file.revision_file_id if drawing_file else None,
        drawing_file_name=drawing_file.original_filename if drawing_file else None,

        original_file_id=original_file.revision_file_id if original_file else None,
        original_file_name=original_file.original_filename if original_file else None,

        plate_file_id=plate_file.revision_file_id if plate_file else None,
        plate_file_name=plate_file.original_filename if plate_file else None,
    )

    return LotCreateContextDto(
        order_line_id=order_line.order_line_id,
        order_no=order_line.order_no,
        partner_id=order_line.partner_id,
        partner_name=partner.name,
        product_id=product.product_id,
        product_code=product.product_code,
        product_name=product.product_name,
        order_qty=order_line.order_qty,
        uom=order_line.uom,
        due_date=order_line.due_date,
        status=order_line.status,
        panel_width_mm=product.panel_width_mm,
        panel_length_mm=product.panel_length_mm,
        cut_qty_per_panel=product.cut_qty_per_panel,
        product_spec=product.product_spec,
        drawing=drawing_dto,
        primary_lot_candidates=primary_lot_candidates,
        can_create_primary_lot=order_line.status == OrderLineStatus.OPEN.value,
    )

@router.get("/{order_line_id}", response_model=OrderLineOut)
def get_order_line(order_line_id: int, db: Session = Depends(get_db)):
    obj = order_line_crud.get(db, order_line_id)
    if not obj or not obj.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    # 단건에서도 partner/product 표시 필드 채우고 싶으면 join 1회 수행
    partner = db.get(Partner, obj.partner_id)
    product = db.get(Product, obj.product_id)

    out = OrderLineOut.model_validate(obj, from_attributes=True)
    out.partner_name = partner.name if partner else None
    out.product_code = product.product_code if product else None
    out.product_name = product.product_name if product else None
    return out

def _to_status_display(order_status: str) -> str:
    return "IN_PROGRESS" if order_status == OrderLineStatus.CLOSED.value else order_status


def _get_lot_current_process_name(lot: Lot) -> Optional[str]:
    """
    우선순위:
    1) IN_PROGRESS step
    2) 첫 WAITING step
    3) 없으면 None
    """
    in_progress = next((s for s in lot.steps if s.status == "IN_PROGRESS"), None)
    if in_progress:
        return in_progress.process_name

    waiting = next((s for s in lot.steps if s.status == "WAITING"), None)
    if waiting:
        return waiting.process_name

    return None


def _build_detail_timeline(
    order_line: OrderLine,
    lots: list[Lot],
) -> list[OrderLineTimelineItemDto]:
    items: list[OrderLineTimelineItemDto] = []

    items.append(
        OrderLineTimelineItemDto(
            event_type="ORDER_CREATED",
            event_label="수주 생성",
            event_at=order_line.created_at,
            message=f"수주가 등록되었습니다. (수주수량 {order_line.order_qty:,} {order_line.uom})",
            ref_type="ORDER_LINE",
            ref_id=order_line.order_line_id,
        )
    )

    for lot in lots:
        lot_type = "REWORK" if lot.parent_lot_id else "NORMAL"
        label = "재작업 LOT 생성" if lot.parent_lot_id else "기본 LOT 생성"

        items.append(
            OrderLineTimelineItemDto(
                event_type="LOT_CREATED",
                event_label=label,
                event_at=lot.created_at,
                message=f"{lot.lot_no} / {lot_type} / 계획수량 {lot.lot_qty:,} {lot.uom}",
                ref_type="LOT",
                ref_id=lot.lot_id,
            )
        )

        if lot.status == "DONE":
            items.append(
                OrderLineTimelineItemDto(
                    event_type="LOT_DONE",
                    event_label="LOT 완료",
                    event_at=lot.updated_at,
                    message=f"{lot.lot_no} LOT가 완료되었습니다.",
                    ref_type="LOT",
                    ref_id=lot.lot_id,
                )
            )
        elif lot.status == "CANCELED":
            items.append(
                OrderLineTimelineItemDto(
                    event_type="LOT_CANCELED",
                    event_label="LOT 취소",
                    event_at=lot.updated_at,
                    message=f"{lot.lot_no} LOT가 취소되었습니다.",
                    ref_type="LOT",
                    ref_id=lot.lot_id,
                )
            )

    if order_line.status == OrderLineStatus.CANCELED.value:
        items.append(
            OrderLineTimelineItemDto(
                event_type="ORDER_CANCELED",
                event_label="수주 취소",
                event_at=order_line.updated_at,
                message="수주가 취소되었습니다.",
                ref_type="ORDER_LINE",
                ref_id=order_line.order_line_id,
            )
        )

    items.sort(key=lambda x: x.event_at, reverse=True)
    return items


@router.patch("/{order_line_id}/detail", response_model=OrderLineDetailDto)
def update_order_line_detail(
    order_line_id: int,
    payload: OrderLineDetailUpdate,
    db: Session = Depends(get_db),
):
    order_line = order_line_crud.get(db, order_line_id)
    if not order_line or not order_line.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    if order_line.status in {
        OrderLineStatus.DONE.value,
        OrderLineStatus.CANCELED.value,
    }:
        raise HTTPException(
            status_code=409,
            detail="DONE 또는 CANCELED 상태의 수주는 수정할 수 없습니다.",
        )

    lots = (
        db.execute(
            select(Lot)
            .options(selectinload(Lot.steps))
            .where(Lot.order_line_id == order_line_id)
            .order_by(Lot.created_date.asc(), Lot.lot_id.asc())
        )
        .scalars()
        .all()
    )

    # 기본 검증
    if payload.order_qty <= 0:
        raise HTTPException(status_code=422, detail="order_qty must be greater than 0")

    # 수주 수정
    order_line.due_date = payload.due_date
    order_line.order_qty = payload.order_qty
    order_line.memo = payload.memo
    order_line.updated_at = datetime.now(timezone.utc)

    db.add(order_line)
    db.commit()
    db.refresh(order_line)

    partner = db.get(Partner, order_line.partner_id)
    product = db.get(Product, order_line.product_id)

    # 갱신 후 LOT 다시 조회
    lots = (
        db.execute(
            select(Lot)
            .options(selectinload(Lot.steps))
            .where(Lot.order_line_id == order_line_id)
            .order_by(Lot.created_date.asc(), Lot.lot_id.asc())
        )
        .scalars()
        .all()
    )

    has_any_lot = len(lots) > 0
    has_base_lot = any(l.parent_lot_id is None for l in lots)

    can_edit = order_line.status in {
        OrderLineStatus.OPEN.value,
        OrderLineStatus.CLOSED.value,
    }
    can_save = can_edit

    can_cancel_order = (
        order_line.status not in {OrderLineStatus.DONE.value, OrderLineStatus.CANCELED.value}
        and (
            not has_any_lot
            or all(l.status == "CANCELED" for l in lots)
        )
    )

    can_create_base_lot = (
        order_line.status == OrderLineStatus.OPEN.value
        and not has_base_lot
    )

    lot_items: list[OrderLineDetailLotDto] = []
    for lot in lots:
        is_done_or_canceled = lot.status in {"DONE", "CANCELED"}

        lot_items.append(
            OrderLineDetailLotDto(
                lot_id=lot.lot_id,
                lot_no=lot.lot_no,
                lot_type="REWORK" if lot.parent_lot_id else "NORMAL",
                parent_lot_id=lot.parent_lot_id,
                lot_qty=lot.lot_qty,
                status=lot.status,
                current_process_name=_get_lot_current_process_name(lot),
                is_editable=not is_done_or_canceled,
                can_cancel=not is_done_or_canceled,
                can_create_rework=is_done_or_canceled,
            )
        )

    timeline = _build_detail_timeline(order_line, lots)

    return OrderLineDetailDto(
        order_line_id=order_line.order_line_id,
        order_no=order_line.order_no,
        line_no=order_line.line_no,
        partner_id=order_line.partner_id,
        partner_name=partner.name if partner else "",
        product_id=order_line.product_id,
        product_code=product.product_code if product else "",
        product_name=product.product_name if product else "",
        order_date=order_line.order_date,
        due_date=order_line.due_date,
        order_qty=order_line.order_qty,
        uom=order_line.uom,
        customer_po=order_line.customer_po,
        memo=order_line.memo,
        status=order_line.status,
        status_display=_to_status_display(order_line.status),
        is_active=order_line.is_active,
        can_edit=can_edit,
        can_save=can_save,
        can_cancel_order=can_cancel_order,
        can_create_base_lot=can_create_base_lot,
        lots=lot_items,
        timeline=timeline,
    )

@router.post("/{order_line_id}/cancel", response_model=OrderLineDetailDto)
def cancel_order_line(
    order_line_id: int,
    db: Session = Depends(get_db),
):
    order_line = order_line_crud.get(db, order_line_id)
    if not order_line or not order_line.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    if order_line.status == OrderLineStatus.DONE.value:
        raise HTTPException(
            status_code=409,
            detail="DONE 상태의 수주는 취소할 수 없습니다.",
        )

    if order_line.status == OrderLineStatus.CANCELED.value:
        raise HTTPException(
            status_code=409,
            detail="이미 취소된 수주입니다.",
        )

    lots = (
        db.execute(
            select(Lot)
            .options(selectinload(Lot.steps))
            .where(Lot.order_line_id == order_line_id)
            .order_by(Lot.created_date.asc(), Lot.lot_id.asc())
        )
        .scalars()
        .all()
    )

    # LOT가 존재하면 전부 CANCELED여야만 수주취소 가능
    if lots and any(l.status != "CANCELED" for l in lots):
        raise HTTPException(
            status_code=409,
            detail="취소되지 않은 LOT가 존재하여 수주를 취소할 수 없습니다. 먼저 모든 LOT를 취소하세요.",
        )

    order_line.status = OrderLineStatus.CANCELED.value
    order_line.updated_at = datetime.now(timezone.utc)

    db.add(order_line)
    db.commit()
    db.refresh(order_line)

    partner = db.get(Partner, order_line.partner_id)
    product = db.get(Product, order_line.product_id)

    # 취소 후 다시 조회
    lots = (
        db.execute(
            select(Lot)
            .options(selectinload(Lot.steps))
            .where(Lot.order_line_id == order_line_id)
            .order_by(Lot.created_date.asc(), Lot.lot_id.asc())
        )
        .scalars()
        .all()
    )

    has_base_lot = any(l.parent_lot_id is None for l in lots)

    can_edit = False
    can_save = False
    can_cancel_order = False
    can_create_base_lot = False

    lot_items: list[OrderLineDetailLotDto] = []
    for lot in lots:
        is_done_or_canceled = lot.status in {"DONE", "CANCELED"}

        lot_items.append(
            OrderLineDetailLotDto(
                lot_id=lot.lot_id,
                lot_no=lot.lot_no,
                lot_type="REWORK" if lot.parent_lot_id else "NORMAL",
                parent_lot_id=lot.parent_lot_id,
                lot_qty=lot.lot_qty,
                status=lot.status,
                current_process_name=_get_lot_current_process_name(lot),
                is_editable=not is_done_or_canceled,
                can_cancel=not is_done_or_canceled,
                can_create_rework=is_done_or_canceled,
            )
        )

    timeline = _build_detail_timeline(order_line, lots)

    return OrderLineDetailDto(
        order_line_id=order_line.order_line_id,
        order_no=order_line.order_no,
        line_no=order_line.line_no,
        partner_id=order_line.partner_id,
        partner_name=partner.name if partner else "",
        product_id=order_line.product_id,
        product_code=product.product_code if product else "",
        product_name=product.product_name if product else "",
        order_date=order_line.order_date,
        due_date=order_line.due_date,
        order_qty=order_line.order_qty,
        uom=order_line.uom,
        customer_po=order_line.customer_po,
        memo=order_line.memo,
        status=order_line.status,
        status_display=_to_status_display(order_line.status),
        is_active=order_line.is_active,
        can_edit=can_edit,
        can_save=can_save,
        can_cancel_order=can_cancel_order,
        can_create_base_lot=can_create_base_lot,
        lots=lot_items,
        timeline=timeline,
    )


def _has_any_non_canceled_lot(lots: list[Lot]) -> bool:
    return any(l.status != "CANCELED" for l in lots)

def _sync_lot_due_date_for_not_started(db: Session, order_line_id: int, new_due_date: date) -> int:
    """
    OrderLine.due_date 변경 시:
    - 아직 시작 안 한 LOT(= lot_step 중 WAITING 아닌 것이 없음)만 lot.due_date를 동기화
    """
    started_exists = (
        select(LotStep.lot_step_id)
        .where(and_(LotStep.lot_id == Lot.lot_id, LotStep.status != "WAITING"))
        .limit(1)
    )

    stmt = (
        update(Lot)
        .where(Lot.order_line_id == order_line_id)
        .where(~exists(started_exists))
        .values(due_date=new_due_date)
    )

    result = db.execute(stmt)
    return result.rowcount or 0