from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select, or_
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.db.session import get_db
from fastapi.responses import FileResponse
from app.models.inspection_defect_attachment import InspectionDefectAttachment
from app.models.inspection_result import InspectionResult
from app.models.inspection_schedule import InspectionSchedule
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.partner import Partner
from app.models.product import Product
from app.models.product_inventory_movement import ProductInventoryMovement
from app.models.shipment_line import ShipmentLine
from app.schemas.inspection_result import InspectionInventorySummaryOut
from app.services.inventory_fifo_service import get_available_inventory_lots_fifo
from app.services.order_line_plan_service import get_latest_plan_history
from app.services.ship_qty_policy import calculate_ship_qty


from app.schemas.inspection_result import (
    DefectAttachmentUploadOut,
    InspectionAccumulatedSummaryOut,
    InspectionResultGetOut,
    InspectionResultListItemOut,
    InspectionResultUpsertIn,
    InspectionResultUpsertOut,
)
from app.services.inspection_result_service import upsert_inspection_result

router = APIRouter(prefix="/inspection-schedules", tags=["InspectionResult"])

_filename_safe_re = re.compile(r"[^\w.()-]+", re.UNICODE)


def _safe_filename(name: str) -> str:
    name = (name or "").strip().replace(" ", "_")
    name = _filename_safe_re.sub("_", name)
    return name[:150] if len(name) > 150 else name


def _ext_of(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")

def _normalize_allowed_exts(values) -> set[str]:
    return {
        str(value).strip().lower().lstrip(".")
        for value in values
        if str(value).strip()
    }


def _abs_path_from_uri(file_uri: str) -> Path:
    root = Path(settings.DEFECT_PHOTO_STORAGE_ROOT).resolve()
    abs_path = (root / file_uri).resolve()

    try:
        abs_path.relative_to(root)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid attachment path",
        )

    return abs_path

def _ensure_schedule(db: Session, inspection_schedule_id: int) -> InspectionSchedule:
    obj = db.execute(
        select(InspectionSchedule).where(
            InspectionSchedule.inspection_schedule_id == inspection_schedule_id
        )
    ).scalar_one_or_none()

    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="InspectionSchedule not found",
        )

    return obj


def _make_defect_photo_dir(*, inspection_schedule_id: int) -> Path:
    root = Path(settings.DEFECT_PHOTO_STORAGE_ROOT)
    return root / "defect_photos" / str(inspection_schedule_id)


def _save_defect_photo(
    *,
    file: UploadFile,
    target_dir: Path,
    inspection_schedule_id: int,
) -> tuple[str, str, int, str | None]:
    ext = _ext_of(file.filename or "")
    allowed_exts = _normalize_allowed_exts(settings.DEFECT_PHOTO_ALLOWED_EXT)

    if not ext or ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. allowed={sorted(allowed_exts)}",
        )

    root = Path(settings.DEFECT_PHOTO_STORAGE_ROOT).resolve()
    target_dir = target_dir.resolve()

    try:
        target_dir.relative_to(root)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid storage path",
        )

    target_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    original = _safe_filename(file.filename or f"file.{ext}")
    final_name = f"{ts}_{uuid4().hex[:8]}_{original}"
    abs_path = target_dir / final_name

    max_bytes = settings.DEFECT_PHOTO_MAX_MB * 1024 * 1024
    written = 0

    with abs_path.open("wb") as f:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break

            written += len(chunk)

            if written > max_bytes:
                try:
                    abs_path.unlink(missing_ok=True)
                except Exception:
                    pass

                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. max={settings.DEFECT_PHOTO_MAX_MB}MB",
                )

            f.write(chunk)

    if written <= 0:
        try:
            abs_path.unlink(missing_ok=True)
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file is not allowed",
        )

    rel_uri = str(abs_path.resolve().relative_to(root))
    return rel_uri.replace("\\", "/"), original, written, file.content_type


def _get_accumulated_summary(
    db: Session,
    *,
    inspection_schedule_id: int,
) -> InspectionAccumulatedSummaryOut:
    current_schedule = _ensure_schedule(db, inspection_schedule_id)
    lot_id = current_schedule.lot_id

    row = db.execute(
        select(
            func.coalesce(func.sum(InspectionResult.good_qty), 0),
            func.coalesce(func.sum(InspectionResult.defect_qty), 0),
            func.coalesce(func.sum(InspectionResult.defect_ship_qty), 0),
            func.coalesce(func.sum(InspectionResult.inspected_qty), 0),
            func.coalesce(func.sum(InspectionResult.discard_qty), 0),
        )
        .select_from(InspectionResult)
        .join(
            InspectionSchedule,
            InspectionSchedule.inspection_schedule_id == InspectionResult.inspection_schedule_id,
        )
        .where(
            InspectionSchedule.lot_id == lot_id,
            InspectionSchedule.inspection_schedule_id != inspection_schedule_id,
            InspectionSchedule.status.in_(("PARTIAL_DONE", "DONE")),
        )
    ).one()

    return InspectionAccumulatedSummaryOut(
        good_qty=int(row[0] or 0),
        defect_qty=int(row[1] or 0),
        defect_ship_qty=int(row[2] or 0),
        inspected_qty=int(row[3] or 0),
        discard_qty=int(row[4] or 0),
    )

def _get_inventory_summary(
    db: Session,
    *,
    inspection_schedule_id: int,
    current_result_id: int | None,
) -> InspectionInventorySummaryOut:
    current_schedule = _ensure_schedule(db, inspection_schedule_id)

    lot = db.execute(
        select(Lot).where(Lot.lot_id == current_schedule.lot_id)
    ).scalar_one_or_none()
    if lot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lot not found",
        )

    order_line = db.execute(
        select(OrderLine).where(OrderLine.order_line_id == lot.order_line_id)
    ).scalar_one_or_none()
    if order_line is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OrderLine not found",
        )

    partner = db.get(Partner, order_line.partner_id)
    partner_name = partner.name if partner else ""

    current_result_stock_ship_qty = 0
    current_result_result_ship_qty = 0
    current_result_stock_in_qty = 0
    current_result_discard_qty = 0

    available_stock_lots = get_available_inventory_lots_fifo(
        db,
        product_id=lot.product_id,
        exclude_lot_no=lot.lot_no,
        exclude_inspection_result_id=current_result_id,
    )
    current_stock_qty = sum(available_qty for _, available_qty in available_stock_lots)

    if current_result_id is not None:
        result = db.get(InspectionResult, current_result_id)
        if result is not None:
            current_result_discard_qty = int(result.discard_qty or 0)

        current_result_stock_ship_qty = int(
            db.execute(
                select(func.coalesce(func.sum(ShipmentLine.ship_qty), 0)).where(
                    ShipmentLine.inspection_result_id == current_result_id,
                    ShipmentLine.source_type == "STOCK",
                    ShipmentLine.status != "CANCELED",
                )
            ).scalar_one()
            or 0
        )

        current_result_result_ship_qty = int(
            db.execute(
                select(func.coalesce(func.sum(ShipmentLine.ship_qty), 0)).where(
                    ShipmentLine.inspection_result_id == current_result_id,
                    ShipmentLine.source_type == "INSPECTION_RESULT",
                    ShipmentLine.status != "CANCELED",
                )
            ).scalar_one()
            or 0
        )

        sellable_qty = 0
        if result is not None:
            if result.is_partial:
                sellable_qty = 0
            else:
                accumulated = _get_accumulated_summary(
                    db,
                    inspection_schedule_id=inspection_schedule_id,
                )
                sellable_qty = (
                    int(accumulated.good_qty or 0)
                    + int(accumulated.defect_ship_qty or 0)
                    + int(result.good_qty or 0)
                    + int(result.defect_ship_qty or 0)
                )

        current_result_stock_in_qty = max(
            sellable_qty - current_result_result_ship_qty - current_result_discard_qty,
            0,
        )

    else:
        latest_plan = get_latest_plan_history(db, order_line.order_line_id)
        if latest_plan is not None:
            current_result_stock_ship_qty = min(
                int(latest_plan.stock_ship_qty or 0),
                current_stock_qty,
            )

    ship_target_qty = calculate_ship_qty(
        partner_name,
        int(order_line.order_qty),
    )

    shipped_query = select(
        func.coalesce(func.sum(-ProductInventoryMovement.qty), 0)
    ).where(
        ProductInventoryMovement.order_line_id == order_line.order_line_id,
        ProductInventoryMovement.movement_type == "SHIP_OUT",
    )

    already_shipped_qty = db.execute(shipped_query).scalar_one()
    already_shipped_qty = int(already_shipped_qty or 0)

    remaining_ship_target_qty = max(ship_target_qty - already_shipped_qty, 0)

    return InspectionInventorySummaryOut(
        product_id=int(lot.product_id),
        order_line_id=int(order_line.order_line_id),
        current_stock_qty=current_stock_qty,
        order_qty=int(order_line.order_qty),
        ship_target_qty=ship_target_qty,
        already_shipped_qty=already_shipped_qty,
        remaining_ship_target_qty=remaining_ship_target_qty,
        current_result_stock_ship_qty=current_result_stock_ship_qty,
        current_result_result_ship_qty=current_result_result_ship_qty,
        current_result_stock_in_qty=current_result_stock_in_qty,
        current_result_discard_qty=current_result_discard_qty,
    )


@router.get("/results/list", response_model=list[InspectionResultListItemOut])
def list_inspection_results(
    date_from: date | None = None,
    date_to: date | None = None,
    partner_q: str | None = None,
    product_q: str | None = None,
    lot_q: str | None = None,
    created_by_q: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user

    result_ship_sq = (
        select(
            ShipmentLine.inspection_result_id.label("inspection_result_id"),
            func.coalesce(func.sum(ShipmentLine.ship_qty), 0).label("result_ship_qty"),
        )
        .where(
            ShipmentLine.source_type == "INSPECTION_RESULT",
            ShipmentLine.status != "CANCELED",
        )
        .group_by(ShipmentLine.inspection_result_id)
        .subquery()
    )

    inventory_in_sq = (
        select(
            ProductInventoryMovement.inspection_result_id.label("inspection_result_id"),
            func.coalesce(func.sum(ProductInventoryMovement.qty), 0).label("inventory_in_qty"),
        )
        .where(
            ProductInventoryMovement.movement_type == "INSPECTION_IN",
            ProductInventoryMovement.source_type == "INSPECTION_RESULT_IN",
        )
        .group_by(ProductInventoryMovement.inspection_result_id)
        .subquery()
    )

    stmt = (
        select(
            InspectionResult.inspection_result_id,
            InspectionSchedule.inspection_schedule_id,
            Lot.lot_id,
            Lot.lot_no,
            InspectionSchedule.inspection_date,
            OrderLine.due_date,
            Partner.name.label("partner_name"),
            Product.product_code,
            Product.product_name,
            Lot.lot_qty,
            OrderLine.order_qty,
            InspectionResult.good_qty,
            func.coalesce(result_ship_sq.c.result_ship_qty, 0).label("result_ship_qty"),
            InspectionResult.discard_qty,
            (
                func.coalesce(inventory_in_sq.c.inventory_in_qty, 0)
                - func.coalesce(result_ship_sq.c.result_ship_qty, 0)
            ).label("stock_in_qty"),
            InspectionResult.defect_qty,
            InspectionResult.created_by,
            InspectionResult.created_at,
            InspectionResult.updated_at,
            InspectionResult.memo,
        )
        .select_from(InspectionResult)
        .join(
            InspectionSchedule,
            InspectionSchedule.inspection_schedule_id
            == InspectionResult.inspection_schedule_id,
        )
        .join(Lot, Lot.lot_id == InspectionSchedule.lot_id)
        .join(OrderLine, OrderLine.order_line_id == Lot.order_line_id)
        .join(Partner, Partner.partner_id == OrderLine.partner_id)
        .join(Product, Product.product_id == Lot.product_id)
        .outerjoin(
            result_ship_sq,
            result_ship_sq.c.inspection_result_id
            == InspectionResult.inspection_result_id,
        )
        .outerjoin(
            inventory_in_sq,
            inventory_in_sq.c.inspection_result_id
            == InspectionResult.inspection_result_id,
        )
        .where(InspectionSchedule.status == "DONE")
    )

    if date_from is not None:
        stmt = stmt.where(InspectionSchedule.inspection_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(InspectionSchedule.inspection_date <= date_to)
    if partner_q and partner_q.strip():
        stmt = stmt.where(Partner.name.ilike(f"%{partner_q.strip()}%"))
    if product_q and product_q.strip():
        product_keyword = f"%{product_q.strip()}%"
        stmt = stmt.where(
            or_(
                Product.product_name.ilike(product_keyword),
                Product.product_code.ilike(product_keyword),
            )
        )
    if lot_q and lot_q.strip():
        stmt = stmt.where(Lot.lot_no.ilike(f"%{lot_q.strip()}%"))
    if created_by_q and created_by_q.strip():
        stmt = stmt.where(InspectionResult.created_by.ilike(f"%{created_by_q.strip()}%"))

    stmt = stmt.order_by(
        InspectionSchedule.inspection_date.desc(),
        InspectionResult.updated_at.desc(),
        InspectionResult.inspection_result_id.desc(),
    )

    rows = db.execute(stmt).mappings().all()
    return [
        InspectionResultListItemOut(
            inspection_result_id=int(row["inspection_result_id"]),
            inspection_schedule_id=int(row["inspection_schedule_id"]),
            lot_id=int(row["lot_id"]),
            lot_no=str(row["lot_no"] or ""),
            inspection_date=row["inspection_date"],
            due_date=row["due_date"],
            partner_name=str(row["partner_name"] or ""),
            product_code=str(row["product_code"] or ""),
            product_name=str(row["product_name"] or ""),
            lot_qty=int(row["lot_qty"] or 0),
            order_qty=int(row["order_qty"] or 0),
            good_qty=int(row["good_qty"] or 0),
            result_ship_qty=int(row["result_ship_qty"] or 0),
            discard_qty=int(row["discard_qty"] or 0),
            stock_in_qty=max(int(row["stock_in_qty"] or 0), 0),
            defect_qty=int(row["defect_qty"] or 0),
            created_by=row["created_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            memo=row["memo"],
        )
        for row in rows
    ]


@router.get("/{inspection_schedule_id}/result", response_model=InspectionResultGetOut)
def get_result(
    inspection_schedule_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    _ensure_schedule(db, inspection_schedule_id)

    result = db.execute(
        select(InspectionResult).where(
            InspectionResult.inspection_schedule_id == inspection_schedule_id
        )
    ).scalar_one_or_none()

    accumulated = _get_accumulated_summary(
        db,
        inspection_schedule_id=inspection_schedule_id,
    )

    inventory = _get_inventory_summary(
    db,
    inspection_schedule_id=inspection_schedule_id,
    current_result_id=result.inspection_result_id if result else None,
    )

    return InspectionResultGetOut(
        result=result,
        accumulated=accumulated,
        inventory=inventory,
    )


@router.post(
    "/{inspection_schedule_id}/result/photos",
    response_model=DefectAttachmentUploadOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_result_photo(
    inspection_schedule_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user
    _ensure_schedule(db, inspection_schedule_id)

    target_dir = _make_defect_photo_dir(inspection_schedule_id=inspection_schedule_id)
    file_uri, file_name, file_size, mime_type = _save_defect_photo(
        file=file,
        target_dir=target_dir,
        inspection_schedule_id=inspection_schedule_id,
    )

    return {
        "file_uri": file_uri,
        "file_name": file_name,
        "mime_type": mime_type,
        "file_size": file_size,
    }

@router.get("/result/attachments/{attachment_id}/content")
def get_result_attachment_content(
    attachment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ = user

    attachment = db.get(InspectionDefectAttachment, attachment_id)
    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    file_path = _abs_path_from_uri(attachment.file_uri)

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment file not found",
        )

    media_type = attachment.mime_type
    if not media_type:
        suffix = file_path.suffix.lower()
        if suffix in [".jpg", ".jpeg"]:
            media_type = "image/jpeg"
        elif suffix == ".png":
            media_type = "image/png"
        elif suffix == ".gif":
            media_type = "image/gif"
        elif suffix == ".webp":
            media_type = "image/webp"
        else:
            media_type = "application/octet-stream"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=attachment.file_name or file_path.name,
        content_disposition_type="inline",
        headers={"Cache-Control": "no-store"},
    )

@router.put("/{inspection_schedule_id}/result", response_model=InspectionResultUpsertOut)
def put_result(
    inspection_schedule_id: int,
    body: InspectionResultUpsertIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        actor = getattr(user, "username", None) or getattr(user, "login_id", None) or "system"

        result, sch_status, created_next_id = upsert_inspection_result(
            db,
            inspection_schedule_id,
            good_qty=body.good_qty,
            defect_ship_qty=body.defect_ship_qty,
            defect_qty=body.defect_qty,
            stock_ship_qty=body.stock_ship_qty,
            result_ship_qty=body.result_ship_qty,
            stock_in_qty=body.stock_in_qty,
            discard_qty=body.discard_qty,
            is_partial=body.is_partial,
            next_inspection_date=body.next_inspection_date,
            partial_reason=body.partial_reason,
            memo=body.memo,
            defects=body.defects,
            actor=actor,
        )
        db.commit()
        db.refresh(result)

        return {
            "result": result,
            "schedule_status": sch_status,
            "created_next_schedule_id": created_next_id,
        }
    except Exception:
        db.rollback()
        raise
