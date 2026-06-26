# app/api/v1/order_lines.py
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional
from app.models.drawing import Drawing
from app.models.drawing_revision import DrawingRevision
from app.models.drawing_rivision_file import DrawingRevisionFile

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import and_, delete, desc, exists, or_, select, update, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from collections import defaultdict
from app.crud.lot import lot_crud
from app.crud.order_line import order_line_crud
from app.db.session import get_db
from app.models.lot import Lot
from app.models.lot_step import LotStep
from app.models.inspection_certificate import InspectionCertificate
from app.models.inspection_defect import InspectionDefect
from app.models.inspection_defect_attachment import InspectionDefectAttachment
from app.models.inspection_result import InspectionResult
from app.models.inspection_schedule import InspectionSchedule
from app.models.order_line import OrderLine
from app.models.order_line_plan_history import OrderLinePlanHistory
from app.models.outsource_purchase_order_item import OutsourcePurchaseOrderItem
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.outsource_work_instruction_item import OutsourceWorkInstructionItem
from app.models.routing_template_step import RoutingTemplateStep
from app.models.partner import Partner
from app.models.process import Process
from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.shipment_coa import ShipmentCoa
from app.models.shipment_line import ShipmentLine
from app.models.product_inventory_movement import ProductInventoryMovement
from app.services.order_line_plan_service import (
    confirm_order_line_plan_decision,
    create_plan_history as _create_plan_history,
    create_stock_shipment_waiting_for_plan as _create_stock_shipment_waiting_for_plan,
    create_stock_shipment_waiting_if_needed as _create_stock_shipment_waiting_if_needed,
    get_already_shipped_qty as _get_already_shipped_qty,
    get_available_inventory_qty as _get_available_inventory_qty,
    get_latest_plan_history as _get_latest_plan_history,
    get_planned_production_qty as _get_planned_production_qty,
    get_target_ship_qty as _get_target_ship_qty,
)
from app.services.ship_qty_policy import calculate_ship_qty, is_stock_replenishment_partner
from app.services.bulk.order_line_bulk_service import order_line_bulk_service
from app.services.order_line_display import to_plan_type_display
from app.services.production_daily_query import refresh_order_line_snapshot

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
    OrderLinePlanType,
    OrderLinePlanConfirmRequest,
    OrderLinePlanHistoryOut,
    OrderLineBaseLotCreateResult,
    OrderLineShortCloseRequest,
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


def _propagate_order_line_due_date(db: Session, order_line_id: int, new_due_date: date) -> None:
    _sync_lot_due_date_for_not_started(db, order_line_id, new_due_date)
    refresh_order_line_snapshot(db, order_line_id)


def _get_lot_month_code(value: date) -> str:
    month_codes = {
        1: "A",
        2: "B",
        3: "C",
        4: "D",
        5: "E",
        6: "F",
        7: "G",
        8: "H",
        9: "I",
        10: "J",
        11: "K",
        12: "L",
    }
    return month_codes[value.month]


def _generate_lot_no(db: Session, created_date: date, e_fixed: str = "E") -> str:
    yy = f"{created_date.year % 100:02d}"
    dd = f"{created_date.day:02d}"
    month_code = _get_lot_month_code(created_date)
    fixed_code = (e_fixed or "E").strip().upper()
    prefix = f"CT{yy}{month_code}{dd}{fixed_code}"
    legacy_prefix = f"CT{yy}{created_date.month:02d}{dd}0"

    existing_lot_nos = (
        db.execute(
            select(Lot.lot_no)
            .where(or_(Lot.lot_no.like(f"{prefix}%"), Lot.lot_no.like(f"{legacy_prefix}%")))
            .order_by(desc(Lot.lot_no))
        )
        .scalars()
        .all()
    )

    max_seq = 0
    for lot_no in existing_lot_nos:
        try:
            max_seq = max(max_seq, int(lot_no[-2:]))
        except ValueError:
            continue

    nn = max_seq + 1

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
        lot_no = _generate_lot_no(db, created_date, e_fixed="E")

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
                refresh_order_line_snapshot(db, order_line.order_line_id)

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

    actor = "system"

    available_inventory_qty = _get_available_inventory_qty(
        db,
        obj.product_id,
    )

    is_stock_replenishment = is_stock_replenishment_partner(
        partner.name,
        partner.business_no,
    )

    if is_stock_replenishment:
        production_qty = int(obj.order_qty or 0)

        _create_plan_history(
            db,
            order_line=obj,
            plan_type=OrderLinePlanType.STOCK_REPLENISHMENT,
            ship_target_qty=0,
            available_inventory_qty=available_inventory_qty,
            stock_ship_qty=0,
            production_qty=production_qty,
            is_short_close=False,
            memo="발주 등록 자동 처리: 재고비축 생산",
            actor=actor,
        )

        obj.fulfillment_mode = OrderLineFulfillmentMode.PRODUCTION_FIRST.value
        obj.production_policy = OrderLineProductionPolicy.ALLOW_STOCK_BUILD.value
        obj.extra_production_qty = 0
        obj.decision_made = True
        obj.decision_made_at = datetime.now(timezone.utc)
        obj.decision_made_by = actor

        _create_primary_lot_for_order_line(
            db,
            obj,
            product,
            lot_qty=production_qty,
        )

        db.flush()
        return obj

    ship_target_qty = calculate_ship_qty(
        partner.name,
        int(obj.order_qty or 0),
    )

    if ship_target_qty <= 0:
        obj.decision_made = False
        obj.decision_made_at = None
        obj.decision_made_by = None
        db.flush()
        return obj

    if available_inventory_qty <= 0:
        production_qty = ship_target_qty

        _create_plan_history(
            db,
            order_line=obj,
            plan_type=OrderLinePlanType.AUTO_PRODUCTION,
            ship_target_qty=ship_target_qty,
            available_inventory_qty=available_inventory_qty,
            stock_ship_qty=0,
            production_qty=production_qty,
            is_short_close=False,
            memo="발주 등록 자동 처리: 현재고 없음, 생산 진행",
            actor=actor,
        )

        obj.fulfillment_mode = OrderLineFulfillmentMode.PRODUCTION_FIRST.value
        obj.production_policy = OrderLineProductionPolicy.ORDER_ONLY.value
        obj.extra_production_qty = 0
        obj.decision_made = True
        obj.decision_made_at = datetime.now(timezone.utc)
        obj.decision_made_by = actor

        _create_primary_lot_for_order_line(
            db,
            obj,
            product,
            lot_qty=production_qty,
        )

        db.flush()
        return obj

    if available_inventory_qty >= ship_target_qty:
        stock_ship_qty = ship_target_qty

        _create_stock_shipment_waiting_for_plan(
            db,
            order_line=obj,
            ship_qty=stock_ship_qty,
            memo="발주 등록 자동 처리: 재고 출하대기 생성",
        )

        _create_plan_history(
            db,
            order_line=obj,
            plan_type=OrderLinePlanType.AUTO_STOCK_SHIP,
            ship_target_qty=ship_target_qty,
            available_inventory_qty=available_inventory_qty,
            stock_ship_qty=stock_ship_qty,
            production_qty=0,
            is_short_close=False,
            memo="발주 등록 자동 처리: 재고 충분, LOT 없이 출하대기 생성",
            actor=actor,
        )

        obj.fulfillment_mode = OrderLineFulfillmentMode.INVENTORY_FIRST.value
        obj.production_policy = OrderLineProductionPolicy.INVENTORY_ONLY_CLOSE.value
        obj.extra_production_qty = 0
        obj.decision_made = True
        obj.decision_made_at = datetime.now(timezone.utc)
        obj.decision_made_by = actor
        obj.status = OrderLineStatus.DONE.value

        db.flush()
        return obj

    # 부분재고 케이스는 사용자가 처리 방식을 선택해야 하므로 자동 LOT/출하대기를 만들지 않는다.
    # 이후 발주리스트에서 재고만 출고 후 종료 또는 부족분 생산 중 하나를 확정한다.
    obj.fulfillment_mode = OrderLineFulfillmentMode.HYBRID.value
    obj.production_policy = OrderLineProductionPolicy.ORDER_ONLY.value
    obj.extra_production_qty = 0
    obj.decision_made = False
    obj.decision_made_at = None
    obj.decision_made_by = None

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
                detail=f"row_number={row.row_number} 품목명 변경 반영이 불가능합니다.",
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


def _apply_plan_summary_to_out(
    out: OrderLineOut,
    history: OrderLinePlanHistory | None,
) -> OrderLineOut:
    if history is None:
        return out

    out.plan_type = history.plan_type
    out.plan_type_display = to_plan_type_display(history.plan_type)
    return out





def _get_remaining_ship_qty(db: Session, order_line: OrderLine) -> int:
    partner = db.get(Partner, order_line.partner_id)
    partner_name = partner.name if partner else ""

    ship_target_qty = int(calculate_ship_qty(partner_name, int(order_line.order_qty or 0)) or 0)

    already_shipped_qty = int(
        db.execute(
            select(func.coalesce(func.sum(-ProductInventoryMovement.qty), 0)).where(
                ProductInventoryMovement.order_line_id == order_line.order_line_id,
                ProductInventoryMovement.movement_type == "SHIP_OUT",
            )
        ).scalar_one()
        or 0
    )

    return max(ship_target_qty - already_shipped_qty, 0)


        
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
    try:
        obj = _create_order_line_with_policy(db, payload)

        db.commit()
        db.refresh(obj)

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Duplicate order_no+line_no or integrity error",
        )

    partner = db.get(Partner, obj.partner_id)
    product = db.get(Product, obj.product_id)
    latest_plan_history = _get_latest_plan_history(db, obj.order_line_id)

    out = OrderLineOut.model_validate(obj, from_attributes=True)
    out.partner_name = partner.name if partner else None
    out.product_code = product.product_code if product else None
    out.product_name = product.product_name if product else None

    return _apply_plan_summary_to_out(out, latest_plan_history)

@router.post("/{order_line_id}/plan/confirm", response_model=OrderLineOut)
def confirm_order_line_plan(
    order_line_id: int,
    payload: OrderLinePlanConfirmRequest,
    db: Session = Depends(get_db),
):
    try:
        order_line, history, partner, product = confirm_order_line_plan_decision(
            db,
            order_line_id=order_line_id,
            payload=payload,
        )
        db.commit()
        db.refresh(order_line)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="처리계획 확정 중 무결성 오류가 발생했습니다.",
        )

    out = OrderLineOut.model_validate(order_line, from_attributes=True)
    out.partner_name = partner.name
    out.product_code = product.product_code
    out.product_name = product.product_name

    return _apply_plan_summary_to_out(out, history)


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

    partner = db.get(Partner, obj.partner_id)
    partner_name = partner.name if partner else ""

    planned_production_qty = _get_planned_production_qty(db, obj, partner_name)

    if planned_production_qty <= 0:
        _create_stock_shipment_waiting_if_needed(
            db,
            obj,
            partner_name,
        )

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

    # CLOSED 상태에서 due_date 변경을 허용하기 위해 요청된 due_date를 따로 보관한다.
    requested_due_date = data.get("due_date")

    # 상태 기반 수정 제한
    if obj.status == OrderLineStatus.OPEN.value:
        # OPEN: 기존 정책대로 모든 요청 필드 수정을 허용한다.
        pass

    elif obj.status == OrderLineStatus.CLOSED.value:
        # CLOSED: due_date, memo, customer_po만 허용한다.
        allow_keys = {"due_date", "memo", "customer_po"}
        forbidden = set(data.keys()) - allow_keys
        if forbidden:
            raise HTTPException(
                status_code=409,
                detail="CLOSED OrderLine can only modify due_date/memo/customer_po",
            )
        data = {k: v for k, v in data.items() if k in allow_keys}

    else:
        # DONE/CANCELED: 기존 정책대로 memo, customer_po만 허용한다.
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
    # FK validate if changed. In practice this only applies to OPEN updates.
    if "partner_id" in data:
        _ensure_partner_active(db, data["partner_id"])
    if "product_id" in data:
        product = _ensure_product_active(db, data["product_id"])
        data["uom"] = product.uom
   
    try:
        order_line_crud.update(db, obj, data)

        if requested_due_date is not None and requested_due_date != old_due_date:
            _propagate_order_line_due_date(db, order_line_id, requested_due_date)
        else:
            refresh_order_line_snapshot(db, order_line_id)

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate order_no+line_no or integrity error")

    # 표시 필드를 포함해서 반환한다.
    partner = db.get(Partner, obj.partner_id)
    product = db.get(Product, obj.product_id)
    out = OrderLineOut.model_validate(obj, from_attributes=True)
    out.partner_name = partner.name if partner else None
    out.product_code = product.product_code if product else None
    out.product_name = product.product_name if product else None
    return out

def _count_rows(db: Session, model, *conditions) -> int:
    stmt = select(func.count()).select_from(model)
    if conditions:
        stmt = stmt.where(*conditions)
    return int(db.execute(stmt).scalar_one() or 0)


def _delete_rows_by_ids(db: Session, model, id_column, ids: list[int]) -> None:
    if not ids:
        return

    db.execute(delete(model).where(id_column.in_(ids)))


@router.delete("/{order_line_id}")
def delete_order_line(order_line_id: int, db: Session = Depends(get_db)):
    selected_order_line = (
        db.execute(
            select(OrderLine)
            .where(OrderLine.order_line_id == order_line_id)
            .with_for_update()
        )
        .scalar_one_or_none()
    )

    if not selected_order_line or not selected_order_line.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    order_no = selected_order_line.order_no

    order_lines = (
        db.execute(
            select(OrderLine)
            .where(OrderLine.order_no == order_no)
            .with_for_update()
        )
        .scalars()
        .all()
    )

    order_line_ids = [x.order_line_id for x in order_lines]
    if not order_line_ids:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    lots = (
        db.execute(
            select(Lot)
            .where(Lot.order_line_id.in_(order_line_ids))
            .with_for_update()
        )
        .scalars()
        .all()
    )
    lot_ids = [x.lot_id for x in lots]

    schedules = (
        db.execute(
            select(InspectionSchedule)
            .where(InspectionSchedule.lot_id.in_(lot_ids))
            .with_for_update()
        )
        .scalars()
        .all()
        if lot_ids
        else []
    )
    inspection_schedule_ids = [x.inspection_schedule_id for x in schedules]

    results = (
        db.execute(
            select(InspectionResult)
            .where(InspectionResult.inspection_schedule_id.in_(inspection_schedule_ids))
            .with_for_update()
        )
        .scalars()
        .all()
        if inspection_schedule_ids
        else []
    )
    inspection_result_ids = [x.inspection_result_id for x in results]

    shipment_conditions = [ShipmentLine.order_line_id.in_(order_line_ids)]
    if lot_ids:
        shipment_conditions.append(ShipmentLine.lot_id.in_(lot_ids))
    if inspection_result_ids:
        shipment_conditions.append(ShipmentLine.inspection_result_id.in_(inspection_result_ids))

    shipment_lines = (
        db.execute(
            select(ShipmentLine)
            .where(or_(*shipment_conditions))
            .with_for_update()
        )
        .scalars()
        .all()
    )
    shipment_line_ids = [x.shipment_line_id for x in shipment_lines]

    blockers: list[str] = []

    progressed_lot_count = len([x for x in lots if x.status not in {"WAITING", "CANCELED"}])
    if progressed_lot_count > 0:
        blockers.append(f"진행/완료 LOT {progressed_lot_count}건")

    progressed_schedule_count = len([x for x in schedules if x.status not in {"WAITING", "CANCELED"}])
    if progressed_schedule_count > 0:
        blockers.append(f"진행/완료 검수스케줄 {progressed_schedule_count}건")

    done_shipment_count = len([x for x in shipment_lines if x.status == "DONE"])
    if done_shipment_count > 0:
        blockers.append(f"출하확정 데이터 {done_shipment_count}건")

    movement_conditions = [ProductInventoryMovement.order_line_id.in_(order_line_ids)]
    if inspection_result_ids:
        movement_conditions.append(ProductInventoryMovement.inspection_result_id.in_(inspection_result_ids))
    if inspection_schedule_ids:
        movement_conditions.append(ProductInventoryMovement.inspection_schedule_id.in_(inspection_schedule_ids))
    if shipment_line_ids:
        movement_conditions.append(
            and_(
                ProductInventoryMovement.source_type == "SHIPMENT_LINE",
                ProductInventoryMovement.source_id.in_(shipment_line_ids),
            )
        )

    inventory_movement_count = _count_rows(
        db,
        ProductInventoryMovement,
        or_(*movement_conditions),
    )
    if inventory_movement_count > 0:
        blockers.append(f"재고 입출고 이력 {inventory_movement_count}건")

    shipment_coa_count = _count_rows(
        db,
        ShipmentCoa,
        ShipmentCoa.order_line_id.in_(order_line_ids),
    )
    if shipment_coa_count > 0:
        blockers.append(f"출고 COA {shipment_coa_count}건")

    certificate_conditions = []
    if lot_ids:
        certificate_conditions.append(InspectionCertificate.lot_id.in_(lot_ids))
    if inspection_result_ids:
        certificate_conditions.append(InspectionCertificate.basis_inspection_result_id.in_(inspection_result_ids))

    if certificate_conditions:
        certificate_count = _count_rows(
            db,
            InspectionCertificate,
            or_(*certificate_conditions),
        )
        if certificate_count > 0:
            blockers.append(f"검사성적서 {certificate_count}건")

    if lot_ids:
        outsource_work_instruction_count = _count_rows(
            db,
            OutsourceWorkInstructionItem,
            OutsourceWorkInstructionItem.lot_id.in_(lot_ids),
        )
        outsource_work_group_count = _count_rows(
            db,
            OutsourceWorkGroupItem,
            OutsourceWorkGroupItem.lot_id.in_(lot_ids),
        )
        outsource_purchase_order_count = _count_rows(
            db,
            OutsourcePurchaseOrderItem,
            OutsourcePurchaseOrderItem.lot_id.in_(lot_ids),
        )

        outsource_count = (
            outsource_work_instruction_count
            + outsource_work_group_count
            + outsource_purchase_order_count
        )
        if outsource_count > 0:
            blockers.append(f"외주 연결 데이터 {outsource_count}건")

    if blockers:
        raise HTTPException(
            status_code=409,
            detail=(
                f"수주번호 {order_no}는 운영 데이터가 있어 삭제할 수 없습니다. "
                f"삭제 차단 항목: {', '.join(blockers)}"
            ),
        )

    defects = (
        db.execute(
            select(InspectionDefect).where(
                InspectionDefect.inspection_result_id.in_(inspection_result_ids)
            )
        )
        .scalars()
        .all()
        if inspection_result_ids
        else []
    )
    defect_ids = [x.inspection_defect_id for x in defects]

    try:
        _delete_rows_by_ids(
            db,
            InspectionDefectAttachment,
            InspectionDefectAttachment.inspection_defect_id,
            defect_ids,
        )
        _delete_rows_by_ids(
            db,
            InspectionDefect,
            InspectionDefect.inspection_defect_id,
            defect_ids,
        )
        _delete_rows_by_ids(
            db,
            ShipmentLine,
            ShipmentLine.shipment_line_id,
            shipment_line_ids,
        )
        _delete_rows_by_ids(
            db,
            InspectionResult,
            InspectionResult.inspection_result_id,
            inspection_result_ids,
        )
        _delete_rows_by_ids(
            db,
            InspectionSchedule,
            InspectionSchedule.inspection_schedule_id,
            inspection_schedule_ids,
        )

        if lot_ids:
            db.execute(
                update(Lot)
                .where(Lot.parent_lot_id.in_(lot_ids))
                .values(parent_lot_id=None)
            )

        _delete_rows_by_ids(db, LotStep, LotStep.lot_id, lot_ids)
        _delete_rows_by_ids(db, Lot, Lot.lot_id, lot_ids)
        _delete_rows_by_ids(
            db,
            OrderLinePlanHistory,
            OrderLinePlanHistory.order_line_id,
            order_line_ids,
        )
        _delete_rows_by_ids(
            db,
            OrderLine,
            OrderLine.order_line_id,
            order_line_ids,
        )

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                f"수주번호 {order_no} 삭제 중 연결 데이터 제약이 발생했습니다. "
                "출하, 외주, 검수, 재고 관련 데이터를 확인하세요."
            ),
        )

    return {
        "success": True,
        "order_no": order_no,
        "deleted_order_line_count": len(order_line_ids),
        "deleted_lot_count": len(lot_ids),
        "deleted_shipment_line_count": len(shipment_line_ids),
    }


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

    plan_histories = (
        db.execute(
            select(OrderLinePlanHistory)
            .where(OrderLinePlanHistory.order_line_id == order_line_id)
            .order_by(
                OrderLinePlanHistory.created_at.asc(),
                OrderLinePlanHistory.plan_history_id.asc(),
            )
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

    # 수주 취소 가능 조건:
    # - 연결 LOT가 없거나
    # - 연결 LOT가 모두 CANCELED이고
    # - 수주 자체가 DONE/CANCELED가 아니어야 한다.
    can_cancel_order = (
        order_line.status not in {OrderLineStatus.DONE.value, OrderLineStatus.CANCELED.value}
        and (
            not has_any_lot
            or all(l.status == "CANCELED" for l in lots)
        )
    )

    # 기본 LOT 생성 가능 조건:
    # - 수주 상태 OPEN
    # - 아직 기본 LOT가 없음
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
    timeline.extend(_build_plan_history_timeline_items(plan_histories))
    timeline.sort(key=lambda x: x.event_at)

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

    latest_plan_history = _get_latest_plan_history(db, order_line.order_line_id)

    if latest_plan_history is not None:
        planned_production_qty = int(latest_plan_history.production_qty or 0)
    else:
        planned_production_qty = _get_planned_production_qty(db, order_line, partner.name)

    if planned_production_qty <= 0:
        raise HTTPException(
            status_code=409,
            detail="계획 생산수량이 0이어서 기본 LOT를 생성할 수 없습니다.",
        )

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

    # 화면 표시용 partner/product 필드를 채워 반환한다.
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

def _to_plan_timeline_message(history: OrderLinePlanHistory) -> str:
    plan_type = history.plan_type

    ship_target_qty = int(history.ship_target_qty or 0)
    available_inventory_qty = int(history.available_inventory_qty or 0)
    stock_ship_qty = int(history.stock_ship_qty or 0)
    production_qty = int(history.production_qty or 0)

    if plan_type == "AUTO_PRODUCTION":
        return (
            f"처리계획 확정: 현재고 없음, "
            f"출고목표수량 {ship_target_qty:,}개 기준으로 "
            f"생산필요수량 {production_qty:,}개 생산을 진행합니다."
        )

    if plan_type == "AUTO_STOCK_SHIP":
        return (
            f"처리계획 확정: 현재고 {available_inventory_qty:,}개 중 "
            f"{stock_ship_qty:,}개를 재고 출하대기로 생성했습니다."
        )

    if plan_type == "PARTIAL_STOCK_ONLY_CLOSE":
        return (
            f"처리계획 확정: 현재고 {available_inventory_qty:,}개 중 "
            f"{stock_ship_qty:,}개만 출하하고 부족분 생산 없이 종료합니다."
        )

    if plan_type == "PARTIAL_STOCK_PLUS_PRODUCTION":
        return (
            f"처리계획 확정: 현재고 {available_inventory_qty:,}개 사용 예정, "
            f"부족분 {production_qty:,}개 생산 후 출고목표수량 "
            f"{ship_target_qty:,}개를 맞춥니다."
        )

    if plan_type == "STOCK_REPLENISHMENT":
        return (
            f"처리계획 확정: 재고비축 목적 발주로 "
            f"{production_qty:,}개 생산 후 재고로 입고합니다."
        )

    return "처리계획이 확정되었습니다."


def _build_plan_history_timeline_items(
    plan_histories: list[OrderLinePlanHistory],
) -> list[OrderLineTimelineItemDto]:
    items: list[OrderLineTimelineItemDto] = []

    for history in plan_histories:
        message = _to_plan_timeline_message(history)

        if history.memo:
            message = f"{message} 메모: {history.memo}"

        items.append(
            OrderLineTimelineItemDto(
                event_type="PLAN_CONFIRMED",
                event_label="처리계획 확정",
                event_at=history.created_at,
                message=message,
                ref_type="ORDER_LINE_PLAN_HISTORY",
                ref_id=history.plan_history_id,
            )
        )

    return items

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

    old_due_date = order_line.due_date

    # 수주 수정
    order_line.due_date = payload.due_date
    order_line.order_qty = payload.order_qty
    order_line.memo = payload.memo
    order_line.updated_at = datetime.now(timezone.utc)

    db.add(order_line)
    if payload.due_date != old_due_date:
        _propagate_order_line_due_date(db, order_line_id, payload.due_date)
    else:
        refresh_order_line_snapshot(db, order_line_id)

    db.commit()
    db.refresh(order_line)

    partner = db.get(Partner, order_line.partner_id)
    product = db.get(Product, order_line.product_id)

    # 갱신 후 LOT를 다시 조회한다.
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

@router.patch("/{order_line_id}/short-close", response_model=OrderLineOut)
def short_close_order_line(
    order_line_id: int,
    payload: OrderLineShortCloseRequest,
    db: Session = Depends(get_db),
):
    obj = order_line_crud.get(db, order_line_id)
    if not obj or not obj.is_active:
        raise HTTPException(status_code=404, detail="OrderLine not found")

    if obj.status != OrderLineStatus.CLOSED.value:
        raise HTTPException(status_code=409, detail="부족종료는 CLOSED 상태 수주에서만 가능합니다.")

    remaining_ship_qty = _get_remaining_ship_qty(db, obj)
    if remaining_ship_qty <= 0:
        raise HTTPException(status_code=409, detail="부족수량이 없어 부족종료 대상이 아닙니다.")

    memo_suffix = f"[SHORT_CLOSE] remaining_ship_qty={remaining_ship_qty}"
    if payload.memo and payload.memo.strip():
        memo_suffix = f"{memo_suffix} / {payload.memo.strip()}"

    if obj.memo and obj.memo.strip():
        obj.memo = f"{obj.memo}\n{memo_suffix}"
    else:
        obj.memo = memo_suffix

    obj.status = OrderLineStatus.DONE.value

    db.flush()
    db.commit()
    db.refresh(obj)

    return OrderLineOut.model_validate(obj, from_attributes=True)


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

    # LOT가 존재하면 모두 CANCELED 상태여야 수주 취소가 가능하다.
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

    # 취소 후 다시 조회한다.
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
    OrderLine.due_date 변경 시 아직 시작하지 않은 LOT만 lot.due_date를 동기화한다.
    시작 여부는 WAITING이 아닌 lot_step 존재 여부로 판단한다.
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
