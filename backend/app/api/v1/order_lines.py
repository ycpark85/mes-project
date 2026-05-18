# app/api/v1/order_lines.py
from __future__ import annotations

from datetime import date,datetime, timezone
from typing import Optional
from app.models.drawing import Drawing
from app.models.drawing_revision import DrawingRevision
from app.models.drawing_rivision_file import DrawingRevisionFile

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import and_, desc, exists, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from collections import defaultdict
from app.crud.lot import lot_crud
from app.crud.order_line import order_line_crud
from app.db.session import get_db  # 너희 프로젝트의 get_db 경로에 맞춰 수정
from app.models.lot import Lot
from app.models.lot_step import LotStep
from app.models.order_line import OrderLine
from app.models.routing_template_step import RoutingTemplateStep
from app.models.partner import Partner
from app.models.process import Process
from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.product_inventory_movement import ProductInventoryMovement
from app.services.ship_qty_policy import calculate_ship_qty, is_stock_replenishment_partner
from app.services.bulk.order_line_bulk_service import order_line_bulk_service

from app.schemas.order_line import (
    OrderLineCreate,
    OrderLineUpdate,
    OrderLineOut,
    OrderLineListOut,
    PageMeta,
    OrderLineStatus,
    OrderLineBulkImportRowIn,
    OrderLineBulkValidateRequest,
    OrderLineBulkValidateResult,
    OrderLineBulkCommitRequest,
    OrderLineBulkCommitResult,
    OrderLineBulkCommitGroupResult,
    OrderLineFulfillmentMode,
    OrderLineProductionPolicy,
    OrderLineFulfillmentPlanUpdate,
    OrderLineBaseLotCreateResult,
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


def _generate_lot_no(db: Session, created_date: date, e_fixed: str = "0") -> str:
    yy = f"{created_date.year % 100:02d}"
    mm = f"{created_date.month:02d}"
    dd = f"{created_date.day:02d}"
    prefix = f"CT{yy}{mm}{dd}{e_fixed}"

    last = (
        db.execute(
            select(Lot.lot_no)
            .where(Lot.lot_no.like(f"{prefix}%"))
            .order_by(desc(Lot.lot_no))
            .limit(1)
        )
        .scalar_one_or_none()
    )

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


def _create_lot_steps_from_routing(db: Session, lot_id: int, routing_template_id: int) -> None:
    steps = (
        db.execute(
            select(RoutingTemplateStep)
            .where(
                RoutingTemplateStep.routing_template_id == routing_template_id,
                RoutingTemplateStep.is_active == True,  # noqa: E712
            )
            .order_by(RoutingTemplateStep.step_seq.asc())
        )
        .scalars()
        .all()
    )

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


def _create_primary_lot_for_order_line(
    db: Session,
    order_line: OrderLine,
    product: Product,
    *,
    lot_qty: int | None = None,
) -> Lot:
    if order_line.status != OrderLineStatus.OPEN.value:
        raise HTTPException(
            status_code=409,
            detail="Primary LOT can only be auto-created when OrderLine is OPEN",
        )

    if not product.routing_template_id:
        raise HTTPException(status_code=409, detail="Product has no routing template")

    create_lot_qty = int(lot_qty if lot_qty is not None else order_line.order_qty)

    if create_lot_qty <= 0:
        raise HTTPException(status_code=409, detail="LOT quantity must be greater than zero")

    created_date = date.today()

    for _ in range(3):
        lot_no = _generate_lot_no(db, created_date, e_fixed="0")

        lot = Lot(
            lot_no=lot_no,
            order_line_id=order_line.order_line_id,
            product_id=order_line.product_id,
            parent_lot_id=None,
            lot_qty=create_lot_qty,
            uom=order_line.uom,
            material_lot_no=None,
            material_used_qty=None,
            material_sheet_count=None,
            created_date=created_date,
            due_date=order_line.due_date,
            memo=None,
            status="WAITING",
        )

        try:
            with db.begin_nested():
                lot_crud.create(db, lot)
                _create_lot_steps_from_routing(db, lot.lot_id, product.routing_template_id)

                order_line.status = OrderLineStatus.CLOSED.value

                db.flush()
                db.refresh(lot)

                return lot

        except IntegrityError:
            continue

    raise HTTPException(status_code=409, detail="Failed to generate unique lot_no (retry exceeded)")

def _apply_stock_fulfillment_for_order_line(
    db: Session,
    *,
    order_line: OrderLine,
    partner: Partner,
) -> int:
    ship_target_qty = calculate_ship_qty(
        partner.name,
        int(order_line.order_qty),
    )

    inventory = (
        db.execute(
            select(ProductInventory)
            .where(ProductInventory.product_id == order_line.product_id)
            .with_for_update()
        )
        .scalar_one_or_none()
    )

    current_qty = int(inventory.current_qty or 0) if inventory else 0

    if current_qty <= 0:
        return ship_target_qty

    ship_qty = min(current_qty, ship_target_qty)

    if ship_qty <= 0:
        return ship_target_qty

    inventory.current_qty = current_qty - ship_qty

    db.add(
        ProductInventoryMovement(
            product_id=order_line.product_id,
            movement_type="SHIP_OUT",
            qty=-ship_qty,
            balance_after=inventory.current_qty,
            source_type="ORDER_STOCK_FULFILLMENT",
            source_id=order_line.order_line_id,
            order_line_id=order_line.order_line_id,
            memo=f"발주 등록 재고 충당 출고 / 목표 {ship_target_qty}",
        )
    )

    db.flush()

    return max(ship_target_qty - ship_qty, 0)

def _create_order_line_with_policy(db: Session, payload: OrderLineCreate) -> OrderLine:
    partner = _ensure_partner_active(db, payload.partner_id)
    product = _ensure_product_active(db, payload.product_id)

    data = payload.model_dump()
    data["uom"] = product.uom

    obj = OrderLine(**data)
    order_line_crud.create(db, obj)
    db.flush()

    if is_stock_replenishment_partner(partner.name, partner.business_no):
        _create_primary_lot_for_order_line(
            db,
            obj,
            product,
            lot_qty=int(obj.order_qty),
        )
    else:
        shortage_qty = _apply_stock_fulfillment_for_order_line(
            db=db,
            order_line=obj,
            partner=partner,
        )

        if shortage_qty > 0:
            _create_primary_lot_for_order_line(
                db,
                obj,
                product,
                lot_qty=shortage_qty,
            )
        else:
            obj.status = OrderLineStatus.DONE.value

    db.flush()
    return obj

def _build_bulk_group_memo(items_by_order_no: dict[str, list[OrderLineBulkImportRowIn]], erp_order_no: str) -> str | None:
    remarks: list[str] = []

    for item in items_by_order_no.get(erp_order_no, []):
        remark = (item.remark or "").strip()
        if remark and remark not in remarks:
            remarks.append(remark)

    if not remarks:
        return None

    if len(remarks) == 1:
        return remarks[0]

    return "\n".join(remarks)


def _validate_product_name_change_choices(group, choice_map: dict[int, bool]) -> None:
    product_updates: dict[int, set[tuple[str | None, str | None]]] = defaultdict(set)

    for row in group.rows:
        if not choice_map.get(row.row_number, False):
            continue

        if not row.product_name_mismatch:
            continue

        if not row.can_apply_product_name_change:
            raise HTTPException(
                status_code=409,
                detail=f"row_number={row.row_number} 는 품목명 변경 반영이 불가능합니다.",
            )

        product_updates[row.product_id].add(
            (row.parsed_product_name, row.parsed_product_spec)
        )

    for product_id, values in product_updates.items():
        if len(values) > 1:
            raise HTTPException(
                status_code=409,
                detail=f"같은 품목(product_id={product_id})에 서로 다른 품목명 변경이 동시에 요청되었습니다.",
            )
        
def _get_available_inventory_qty(db: Session, product_id: int) -> int:
    inventory = (
        db.execute(
            select(ProductInventory)
            .where(ProductInventory.product_id == product_id)
        )
        .scalar_one_or_none()
    )
    return int(inventory.current_qty or 0) if inventory else 0


def _get_target_ship_qty(order_line: OrderLine, partner_name: str) -> int:
    return int(calculate_ship_qty(partner_name or "", int(order_line.order_qty or 0)) or 0)


def _get_planned_production_qty(
    db: Session,
    order_line: OrderLine,
    partner_name: str,
) -> int:
    available_inventory_qty = _get_available_inventory_qty(db, order_line.product_id)
    target_ship_qty = _get_target_ship_qty(order_line, partner_name)

    fulfillment_mode = order_line.fulfillment_mode or "INVENTORY_FIRST"
    production_policy = order_line.production_policy or "ORDER_ONLY"
    extra_production_qty = int(order_line.extra_production_qty or 0)

    if fulfillment_mode == "PRODUCTION_FIRST":
        base_planned_production_qty = target_ship_qty
    else:
        base_planned_production_qty = max(target_ship_qty - available_inventory_qty, 0)

    if production_policy != "ALLOW_STOCK_BUILD":
        extra_production_qty = 0

    return base_planned_production_qty + extra_production_qty


        
@router.post("/bulk/commit", response_model=OrderLineBulkCommitResult)
def commit_order_lines_bulk(
    payload: OrderLineBulkCommitRequest,
    db: Session = Depends(get_db),
):
    validation = order_line_bulk_service.validate_bulk(
        db,
        OrderLineBulkValidateRequest(items=payload.items),
    )

    items_by_order_no: dict[str, list[OrderLineBulkImportRowIn]] = defaultdict(list)
    for item in payload.items:
        items_by_order_no[item.erp_order_no.strip()].append(item)

    choice_map = {
        item.row_number: item.apply_product_name_change
        for item in payload.row_choices
    }

    results: list[OrderLineBulkCommitGroupResult] = []
    success_group_count = 0
    failure_group_count = 0

    for group in validation.groups:
        if not group.can_commit:
            failure_group_count += 1
            results.append(
                OrderLineBulkCommitGroupResult(
                    erp_order_no=group.erp_order_no,
                    status="ERROR",
                    message="검증 오류가 있어 등록할 수 없습니다.",
                    created_order_line_ids=[],
                )
            )
            continue

        try:
            created_ids: list[int] = []

            with db.begin_nested():
                _validate_product_name_change_choices(group, choice_map)

                group_memo = _build_bulk_group_memo(items_by_order_no, group.erp_order_no)

                for row in group.rows:
                    if row.status == "ERROR":
                        raise HTTPException(
                            status_code=409,
                            detail=f"row_number={row.row_number} 검증 오류로 등록할 수 없습니다.",
                        )

                    if choice_map.get(row.row_number, False) and row.product_name_mismatch:
                        product = db.get(Product, row.product_id)
                        if product is None or not product.is_active:
                            raise HTTPException(
                                status_code=404,
                                detail=f"row_number={row.row_number} 품목을 찾을 수 없습니다.",
                            )

                        if row.parsed_product_name:
                            product.product_name = row.parsed_product_name
                        product.product_spec = row.parsed_product_spec

                        db.add(product)
                        db.flush()

                    create_payload = OrderLineCreate(
                        order_no=row.erp_order_no,
                        line_no=row.line_no,
                        partner_id=row.partner_id,
                        product_id=row.product_id,
                        order_date=row.order_date,
                        due_date=row.due_date,
                        order_qty=row.order_qty,
                        uom="",
                        customer_po=None,
                        memo=group_memo,
                    )

                    created = _create_order_line_with_policy(db, create_payload)
                    created_ids.append(created.order_line_id)

            success_group_count += 1
            results.append(
                OrderLineBulkCommitGroupResult(
                    erp_order_no=group.erp_order_no,
                    status="SUCCESS",
                    message=None,
                    created_order_line_ids=created_ids,
                )
            )

        except HTTPException as exc:
            failure_group_count += 1
            results.append(
                OrderLineBulkCommitGroupResult(
                    erp_order_no=group.erp_order_no,
                    status="ERROR",
                    message=str(exc.detail),
                    created_order_line_ids=[],
                )
            )
        except IntegrityError:
            failure_group_count += 1
            results.append(
                OrderLineBulkCommitGroupResult(
                    erp_order_no=group.erp_order_no,
                    status="ERROR",
                    message="Duplicate order_no+line_no or integrity error",
                    created_order_line_ids=[],
                )
            )

    db.commit()

    return OrderLineBulkCommitResult(
        total_group_count=len(validation.groups),
        success_group_count=success_group_count,
        failure_group_count=failure_group_count,
        groups=results,
    )



@router.post("/bulk/validate", response_model=OrderLineBulkValidateResult)
def validate_order_lines_bulk(
    payload: OrderLineBulkValidateRequest,
    db: Session = Depends(get_db),
):
    return order_line_bulk_service.validate_bulk(db, payload)



@router.post("", response_model=OrderLineOut, status_code=http_status.HTTP_201_CREATED)
def create_order_line(payload: OrderLineCreate, db: Session = Depends(get_db)):
    partner = _ensure_partner_active(db, payload.partner_id)
    product = _ensure_product_active(db, payload.product_id)

    data = payload.model_dump()
    data["uom"] = product.uom

    inventory = (
        db.execute(
            select(ProductInventory)
            .where(ProductInventory.product_id == payload.product_id)
        )
        .scalar_one_or_none()
    )
    available_inventory_qty = int(inventory.current_qty or 0) if inventory else 0

    if available_inventory_qty <= 0:
        recommended_mode = OrderLineFulfillmentMode.PRODUCTION_FIRST.value
    elif available_inventory_qty >= int(payload.order_qty):
        recommended_mode = OrderLineFulfillmentMode.INVENTORY_FIRST.value
    else:
        recommended_mode = OrderLineFulfillmentMode.HYBRID.value

    data["fulfillment_mode"] = recommended_mode
    data["production_policy"] = OrderLineProductionPolicy.ORDER_ONLY.value
    data["extra_production_qty"] = 0
    data["decision_made"] = False
    data["decision_made_at"] = None
    data["decision_made_by"] = None

    obj = OrderLine(**data)

    try:
        order_line_crud.create(db, obj)
        db.commit()
        db.refresh(obj)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate order_no+line_no or integrity error")

    return OrderLineOut.model_validate(obj, from_attributes=True)


@router.patch("/{order_line_id}/fulfillment-plan", response_model=OrderLineOut)
def update_order_line_fulfillment_plan(
    order_line_id: int,
    payload: OrderLineFulfillmentPlanUpdate,
    db: Session = Depends(get_db),
):
    obj = order_line_crud.get(db, order_line_id)
    if not obj or not obj.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    if obj.status in {OrderLineStatus.DONE.value, OrderLineStatus.CANCELED.value}:
        raise HTTPException(status_code=409, detail="DONE 또는 CANCELED 상태의 수주는 처리계획을 변경할 수 없습니다.")

    data = payload.model_dump()

    if data["production_policy"] == OrderLineProductionPolicy.ORDER_ONLY.value:
        data["extra_production_qty"] = 0

    data["decision_made"] = True
    data["decision_made_at"] = datetime.now(timezone.utc)

    order_line_crud.update(db, obj, data)
    db.commit()
    db.refresh(obj)

    return OrderLineOut.model_validate(obj, from_attributes=True)



@router.get("", response_model=OrderLineListOut)
def list_order_lines(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    status_group: Optional[str] = Query(None),
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
        status=status,
        status_group=status_group,
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

@router.post("/{order_line_id}/base-lot", response_model=OrderLineBaseLotCreateResult)
def create_base_lot_from_fulfillment_plan(
    order_line_id: int,
    db: Session = Depends(get_db),
):
    order_line = order_line_crud.get(db, order_line_id)
    if not order_line or not order_line.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    if order_line.status != OrderLineStatus.OPEN.value:
        raise HTTPException(status_code=409, detail="기본 LOT는 OPEN 상태 수주에서만 생성할 수 있습니다.")

    lots = (
        db.execute(
            select(Lot)
            .where(Lot.order_line_id == order_line_id)
            .order_by(Lot.created_date.asc(), Lot.lot_id.asc())
        )
        .scalars()
        .all()
    )

    has_base_lot = any(l.parent_lot_id is None for l in lots)
    if has_base_lot:
        raise HTTPException(status_code=409, detail="이미 기본 LOT가 존재합니다.")

    if not order_line.decision_made:
        raise HTTPException(status_code=409, detail="처리계획이 먼저 저장되어야 합니다.")

    partner = db.get(Partner, order_line.partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    product = db.get(Product, order_line.product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found or inactive")

    planned_production_qty = _get_planned_production_qty(db, order_line, partner.name)
    if planned_production_qty <= 0:
        raise HTTPException(status_code=409, detail="계획 생산수량이 0이어서 기본 LOT를 생성할 수 없습니다.")

    try:
        lot = _create_primary_lot_for_order_line(
            db,
            order_line,
            product,
            lot_qty=planned_production_qty,
        )
        db.commit()
        db.refresh(order_line)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="기본 LOT 생성 중 무결성 오류가 발생했습니다.")

    return OrderLineBaseLotCreateResult(
        order_line_id=order_line.order_line_id,
        planned_production_qty=planned_production_qty,
        created_lot_id=lot.lot_id,
        created_lot_no=lot.lot_no,
        created_lot_qty=lot.lot_qty,
        order_status=order_line.status,
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
        can_create_primary_lot=False,
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