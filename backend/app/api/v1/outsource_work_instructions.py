from __future__ import annotations

from datetime import date, datetime
from typing import List
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status as http_status
from sqlalchemy import and_, exists, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.partner import Partner
from app.models.product import Product
from app.models.routing_template import RoutingTemplate
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.models.outsource_work_instruction_item import OutsourceWorkInstructionItem
from app.models.outsource_work_instruction_file import OutsourceWorkInstructionFile
from app.schemas.outsource_work_instruction import (
    OutsourceWorkInstructionCandidateLotListOut,
    OutsourceWorkInstructionCandidateLotOut,
    OutsourceWorkInstructionCreate,
    OutsourceWorkInstructionOut,
    OutsourceWorkInstructionItemOut,
    OutsourceWorkInstructionFileOut,
    OutsourceWorkInstructionPlateUploadOut,
)

router = APIRouter(prefix="/outsource-work-instructions", tags=["OutsourceWorkInstruction"])

def _normalize_ext(filename: str) -> str:
    return Path(filename).suffix.lower().strip()


def _sanitize_filename(filename: str) -> str:
    name = Path(filename).name
    return name.replace(" ", "_")


def _validate_plate_data_upload(file: UploadFile, size_bytes: int) -> None:
    original_name = file.filename or ""
    ext = _normalize_ext(original_name)

    if not original_name.strip():
        raise HTTPException(status_code=400, detail="File name is required")

    allowed_ext = settings.PLATE_DATA_ALLOWED_EXT
    if allowed_ext and ext not in allowed_ext:
        raise HTTPException(
            status_code=409,
            detail=f"File extension not allowed: {ext}",
        )

    max_bytes = settings.PLATE_DATA_MAX_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=409,
            detail=f"File size exceeded: max {settings.PLATE_DATA_MAX_MB}MB",
        )


def _build_plate_data_path(filename: str, uploaded_at: datetime) -> Path:
    safe_name = _sanitize_filename(filename)
    y = f"{uploaded_at.year:04d}"
    m = f"{uploaded_at.month:02d}"
    d = f"{uploaded_at.day:02d}"

    root = Path(settings.PLATE_DATA_STORAGE_ROOT)
    folder = root / "plate_data" / y / m / d
    folder.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid4().hex}_{safe_name}"
    return folder / stored_name


def _generate_instruction_no(db: Session, instruction_date: date) -> str:
    yy = f"{instruction_date.year % 100:02d}"
    mm = f"{instruction_date.month:02d}"
    dd = f"{instruction_date.day:02d}"
    prefix = f"OWI{yy}{mm}{dd}"

    last = (
        db.execute(
            select(OutsourceWorkInstruction.instruction_no)
            .where(OutsourceWorkInstruction.instruction_no.like(f"{prefix}%"))
            .order_by(OutsourceWorkInstruction.instruction_no.desc())
            .limit(1)
        )
        .scalar_one_or_none()
    )

    if not last:
        seq = 1
    else:
        try:
            seq = int(last[-3:]) + 1
        except ValueError:
            seq = 1

    return f"{prefix}{seq:03d}"

@router.post(
    "/upload-plate-data",
    response_model=OutsourceWorkInstructionPlateUploadOut,
    status_code=http_status.HTTP_201_CREATED,
)
async def upload_plate_data(
    file: UploadFile = File(...),
):
    uploaded_at = datetime.now()
    content = await file.read()
    size_bytes = len(content)

    _validate_plate_data_upload(file, size_bytes)

    target_path = _build_plate_data_path(file.filename or "plate_data.bin", uploaded_at)

    try:
        target_path.write_bytes(content)
    except OSError:
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    return OutsourceWorkInstructionPlateUploadOut(
        file_name=Path(file.filename or target_path.name).name,
        file_path=str(target_path),
        content_type=file.content_type,
        file_size=size_bytes,
        uploaded_at=uploaded_at,
    )

def _get_available_process_types(template_name: str | None) -> List[str]:
    name = (template_name or "").strip()

    if "무지" in name:
        return ["CUT"]

    if "인쇄" in name:
        return ["CUT", "PRINT"]

    return ["CUT"]


@router.get("/candidates", response_model=OutsourceWorkInstructionCandidateLotListOut)
def get_candidate_lots(
    process_type: str | None = Query(default=None),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if process_type and process_type not in ("CUT", "PRINT"):
        raise HTTPException(status_code=409, detail="Invalid process_type")

    stmt = (
        select(Lot, OrderLine, Product, Partner, RoutingTemplate)
        .join(OrderLine, OrderLine.order_line_id == Lot.order_line_id)
        .join(Product, Product.product_id == Lot.product_id)
        .join(Partner, Partner.partner_id == OrderLine.partner_id)
        .join(RoutingTemplate, RoutingTemplate.routing_template_id == Product.routing_template_id)
        .order_by(Lot.created_date.desc(), Lot.lot_no.asc())
    )

    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            (Lot.lot_no.like(like))
            | (OrderLine.order_no.like(like))
            | (Product.product_code.like(like))
            | (Product.product_name.like(like))
            | (Partner.name.like(like))
        )

    rows = db.execute(stmt).all()
    items: list[OutsourceWorkInstructionCandidateLotOut] = []

    for lot, order_line, product, partner, routing_template in rows:
        available = _get_available_process_types(routing_template.template_name)

        if process_type and process_type not in available:
            continue

        if process_type:
            exists_registered = db.execute(
                select(OutsourceWorkInstructionItem.outsource_work_instruction_item_id)
                .where(
                    OutsourceWorkInstructionItem.lot_id == lot.lot_id,
                    OutsourceWorkInstructionItem.process_type == process_type,
                )
                .limit(1)
            ).scalar_one_or_none()

            if exists_registered:
                continue

        items.append(
            OutsourceWorkInstructionCandidateLotOut(
                lot_id=lot.lot_id,
                lot_no=lot.lot_no,
                order_line_id=order_line.order_line_id,
                order_no=order_line.order_no,
                line_no=order_line.line_no,
                product_id=product.product_id,
                product_code=product.product_code,
                product_name=product.product_name,
                partner_id=partner.partner_id,
                partner_name=partner.name,
                lot_qty=lot.lot_qty,
                available_process_types=available,
            )
        )

    return OutsourceWorkInstructionCandidateLotListOut(items=items)


@router.post("", response_model=OutsourceWorkInstructionOut, status_code=http_status.HTTP_201_CREATED)
def create_outsource_work_instruction(
    payload: OutsourceWorkInstructionCreate,
    db: Session = Depends(get_db),
):
    if payload.process_type not in ("CUT", "PRINT"):
        raise HTTPException(status_code=409, detail="Invalid process_type")

    partner = db.get(Partner, payload.partner_id)
    if not partner or not partner.is_active:
        raise HTTPException(status_code=404, detail="Partner not found or inactive")
    
    if len(payload.lot_ids) > 1:
        if len(payload.files) > 1:
            raise HTTPException(
                status_code=409,
                detail="Bundle work instruction allows only one plate data file",
            )
        
    if payload.process_type == "PRINT" and len(payload.files) == 0:
        raise HTTPException(
            status_code=409,
            detail="PRINT work instruction requires plate data file",
        )  
      
    lots = (
        db.execute(
            select(Lot, OrderLine, Product, RoutingTemplate)
            .join(OrderLine, OrderLine.order_line_id == Lot.order_line_id)
            .join(Product, Product.product_id == Lot.product_id)
            .join(RoutingTemplate, RoutingTemplate.routing_template_id == Product.routing_template_id)
            .where(Lot.lot_id.in_(payload.lot_ids))
        )
        .all()
    )

    if len(lots) != len(set(payload.lot_ids)):
        raise HTTPException(status_code=404, detail="Some lots were not found")

    for lot, order_line, product, routing_template in lots:
        available = _get_available_process_types(routing_template.template_name)
        if payload.process_type not in available:
            raise HTTPException(
                status_code=409,
                detail=f"LOT {lot.lot_no} cannot be registered for process {payload.process_type}",
            )

        exists_registered = db.execute(
            select(OutsourceWorkInstructionItem.outsource_work_instruction_item_id)
            .where(
                OutsourceWorkInstructionItem.lot_id == lot.lot_id,
                OutsourceWorkInstructionItem.process_type == payload.process_type,
            )
            .limit(1)
        ).scalar_one_or_none()

        if exists_registered:
            raise HTTPException(
                status_code=409,
                detail=f"LOT {lot.lot_no} is already registered for process {payload.process_type}",
            )

    instruction = OutsourceWorkInstruction(
        instruction_no=_generate_instruction_no(db, payload.instruction_date),
        instruction_date=payload.instruction_date,
        process_type=payload.process_type,
        partner_id=payload.partner_id,
        is_bundle=len(payload.lot_ids) > 1,
        memo=payload.memo,
    )
    db.add(instruction)
    db.flush()

    for lot_id in payload.lot_ids:
        db.add(
            OutsourceWorkInstructionItem(
                outsource_work_instruction_id=instruction.outsource_work_instruction_id,
                lot_id=lot_id,
                process_type=payload.process_type,
            )
        )

    for file in payload.files:
        db.add(
            OutsourceWorkInstructionFile(
                outsource_work_instruction_id=instruction.outsource_work_instruction_id,
                file_name=file.file_name,
                file_path=file.file_path,
                content_type=file.content_type,
            )
        )

    db.commit()
    db.refresh(instruction)

    item_rows = (
        db.execute(
            select(OutsourceWorkInstructionItem, Lot, OrderLine, Product)
            .join(Lot, Lot.lot_id == OutsourceWorkInstructionItem.lot_id)
            .join(OrderLine, OrderLine.order_line_id == Lot.order_line_id)
            .join(Product, Product.product_id == Lot.product_id)
            .where(
                OutsourceWorkInstructionItem.outsource_work_instruction_id
                == instruction.outsource_work_instruction_id
            )
        )
        .all()
    )

    file_rows = (
        db.execute(
            select(OutsourceWorkInstructionFile)
            .where(
                OutsourceWorkInstructionFile.outsource_work_instruction_id
                == instruction.outsource_work_instruction_id
            )
        )
        .scalars()
        .all()
    )

    return OutsourceWorkInstructionOut(
        outsource_work_instruction_id=instruction.outsource_work_instruction_id,
        instruction_no=instruction.instruction_no,
        instruction_date=instruction.instruction_date,
        process_type=instruction.process_type,
        partner_id=instruction.partner_id,
        is_bundle=instruction.is_bundle,
        memo=instruction.memo,
        created_at=instruction.created_at,
        updated_at=instruction.updated_at,
        items=[
            OutsourceWorkInstructionItemOut(
                outsource_work_instruction_item_id=item.outsource_work_instruction_item_id,
                lot_id=lot.lot_id,
                lot_no=lot.lot_no,
                order_no=order_line.order_no,
                line_no=order_line.line_no,
                product_code=product.product_code,
                product_name=product.product_name,
                lot_qty=lot.lot_qty,
                process_type=item.process_type,
            )
            for item, lot, order_line, product in item_rows
        ],
        files=[OutsourceWorkInstructionFileOut.model_validate(x, from_attributes=True) for x in file_rows],
    )

@router.post(
    "/upload-plate-data",
    response_model=OutsourceWorkInstructionPlateUploadOut,
    status_code=http_status.HTTP_201_CREATED,
)
async def upload_plate_data(
    file: UploadFile = File(...),
):
    uploaded_at = datetime.now()
    content = await file.read()
    size_bytes = len(content)

    _validate_plate_data_upload(file, size_bytes)

    target_path = _build_plate_data_path(file.filename or "plate_data.bin", uploaded_at)

    try:
        target_path.write_bytes(content)
    except OSError:
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    return OutsourceWorkInstructionPlateUploadOut(
        file_name=Path(file.filename or target_path.name).name,
        file_path=str(target_path),
        content_type=file.content_type,
        file_size=size_bytes,
        uploaded_at=uploaded_at,
    )