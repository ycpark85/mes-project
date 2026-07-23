from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.raw_material import (
    RawMaterialAdjustmentIn,
    RawMaterialCreate,
    RawMaterialInboundIn,
    RawMaterialInventoryLotListOut,
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
from app.schemas.self_use_sheet import (
    SelfUseSheetInventoryLotListOut,
    SelfUseSheetInventoryLotOut,
    SelfUseSheetJobCancel,
    SelfUseSheetJobComplete,
    SelfUseSheetJobCreate,
    SelfUseSheetJobListOut,
    SelfUseSheetJobOut,
    SelfUseSheetJobStart,
    SelfUseSheetMovementListOut,
    SelfUseSheetTransferIn,
    SelfUseSheetUseIn,
    SelfUseSheetUseReverseIn,
)
from app.services.raw_material_inventory_service import (
    adjust_raw_material_in_session,
    inbound_raw_material_in_session,
    transfer_raw_material_in_session,
)
from app.services.raw_material_master_service import (
    create_raw_material_in_session,
    create_raw_material_location_in_session,
    deactivate_raw_material_in_session,
    deactivate_raw_material_location_in_session,
    update_raw_material_in_session,
    update_raw_material_location_in_session,
)
from app.services.raw_material_query import (
    list_raw_material_inventory_lots_for_grid,
    list_raw_material_locations_for_grid,
    list_raw_material_movements_for_grid,
    list_raw_materials_for_grid,
)
from app.services.self_use_sheet_service import (
    cancel_self_use_sheet_job,
    complete_self_use_sheet_job,
    create_self_use_sheet_job,
    reverse_self_use_sheet_usage,
    start_self_use_sheet_job,
    transfer_self_use_sheet_inventory,
    use_self_use_sheet_inventory,
)
from app.services.self_use_sheet_query import (
    get_self_use_sheet_job,
    list_self_use_sheet_inventory,
    list_self_use_sheet_jobs,
    list_self_use_sheet_movements,
)

router = APIRouter(prefix="/raw-materials", tags=["RawMaterial"])


@router.get("/self-use-sheet-jobs", response_model=SelfUseSheetJobListOut)
def list_self_use_sheet_job_rows(
    q: str | None = Query(None),
    job_status: str | None = Query(None, alias="status"),
    purpose_type: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return list_self_use_sheet_jobs(
        db,
        q=q,
        status=job_status,
        purpose_type=purpose_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
    )


@router.get("/self-use-sheet-jobs/{job_id}", response_model=SelfUseSheetJobOut)
def get_self_use_sheet_job_row(job_id: int, db: Session = Depends(get_db)):
    return get_self_use_sheet_job(db, job_id)


@router.post(
    "/self-use-sheet-jobs",
    response_model=SelfUseSheetJobOut,
    status_code=status.HTTP_201_CREATED,
)
def create_self_use_sheet_job_row(
    payload: SelfUseSheetJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = create_self_use_sheet_job(db, payload, actor=current_user.login_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


@router.post("/self-use-sheet-jobs/{job_id}/start", response_model=SelfUseSheetJobOut)
def start_self_use_sheet_job_row(
    job_id: int,
    payload: SelfUseSheetJobStart,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = start_self_use_sheet_job(db, job_id, payload, actor=current_user.login_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


@router.post("/self-use-sheet-jobs/{job_id}/complete", response_model=SelfUseSheetJobOut)
def complete_self_use_sheet_job_row(
    job_id: int,
    payload: SelfUseSheetJobComplete,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = complete_self_use_sheet_job(db, job_id, payload, actor=current_user.login_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


@router.post("/self-use-sheet-jobs/{job_id}/cancel", response_model=SelfUseSheetJobOut)
def cancel_self_use_sheet_job_row(
    job_id: int,
    payload: SelfUseSheetJobCancel,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = cancel_self_use_sheet_job(db, job_id, payload, actor=current_user.login_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


@router.get("/self-use-sheet-inventory", response_model=SelfUseSheetInventoryLotListOut)
def list_self_use_sheet_inventory_rows(
    q: str | None = Query(None),
    raw_material_id: int | None = Query(None, ge=1),
    inventory_status: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return list_self_use_sheet_inventory(
        db,
        q=q,
        raw_material_id=raw_material_id,
        status=inventory_status,
        page=page,
        size=size,
    )


@router.get(
    "/self-use-sheet-inventory/{lot_id}/movements",
    response_model=SelfUseSheetMovementListOut,
)
def list_self_use_sheet_movement_rows(
    lot_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return list_self_use_sheet_movements(db, lot_id, page=page, size=size)


@router.get("/self-use-sheet-movements", response_model=SelfUseSheetMovementListOut)
def list_all_self_use_sheet_movement_rows(
    q: str | None = Query(None),
    movement_type: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return list_self_use_sheet_movements(
        db,
        q=q,
        movement_type=movement_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
    )


@router.post(
    "/self-use-sheet-inventory/{lot_id}/use",
    response_model=SelfUseSheetInventoryLotOut,
)
def use_self_use_sheet_inventory_row(
    lot_id: int,
    payload: SelfUseSheetUseIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = use_self_use_sheet_inventory(db, lot_id, payload, actor=current_user.login_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


@router.post(
    "/self-use-sheet-inventory/{lot_id}/transfer",
    response_model=SelfUseSheetInventoryLotOut,
)
def transfer_self_use_sheet_inventory_row(
    lot_id: int,
    payload: SelfUseSheetTransferIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = transfer_self_use_sheet_inventory(db, lot_id, payload, actor=current_user.login_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


@router.post(
    "/self-use-sheet-movements/{movement_id}/reverse",
    response_model=SelfUseSheetInventoryLotOut,
)
def reverse_self_use_sheet_usage_row(
    movement_id: int,
    payload: SelfUseSheetUseReverseIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = reverse_self_use_sheet_usage(db, movement_id, payload, actor=current_user.login_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


@router.post("", response_model=RawMaterialOut, status_code=status.HTTP_201_CREATED)
def create_raw_material(payload: RawMaterialCreate, db: Session = Depends(get_db)):
    try:
        result = create_raw_material_in_session(db, payload)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="material_code already exists")
    except Exception:
        db.rollback()
        raise
    return result


@router.get("", response_model=RawMaterialListOut)
def list_raw_materials(
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    q: str | None = Query(None),
    is_active: bool | None = Query(True),
    db: Session = Depends(get_db),
):
    return list_raw_materials_for_grid(db, page=page, size=size, q=q, is_active=is_active)


@router.patch("/{raw_material_id}", response_model=RawMaterialOut)
def update_raw_material(raw_material_id: int, payload: RawMaterialUpdate, db: Session = Depends(get_db)):
    try:
        result = update_raw_material_in_session(db, raw_material_id=raw_material_id, payload=payload)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


@router.delete("/{raw_material_id}", response_model=RawMaterialOut)
def delete_raw_material(raw_material_id: int, db: Session = Depends(get_db)):
    try:
        result = deactivate_raw_material_in_session(db, raw_material_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


@router.post("/locations", response_model=RawMaterialLocationOut, status_code=status.HTTP_201_CREATED)
def create_location(payload: RawMaterialLocationCreate, db: Session = Depends(get_db)):
    try:
        result = create_raw_material_location_in_session(db, payload)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="location_code already exists")
    except Exception:
        db.rollback()
        raise
    return result


@router.get("/locations", response_model=RawMaterialLocationListOut)
def list_locations(
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    q: str | None = Query(None),
    is_active: bool | None = Query(True),
    db: Session = Depends(get_db),
):
    return list_raw_material_locations_for_grid(db, page=page, size=size, q=q, is_active=is_active)


@router.patch("/locations/{location_id}", response_model=RawMaterialLocationOut)
def update_location(location_id: int, payload: RawMaterialLocationUpdate, db: Session = Depends(get_db)):
    try:
        result = update_raw_material_location_in_session(db, location_id=location_id, payload=payload)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


@router.delete("/locations/{location_id}", response_model=RawMaterialLocationOut)
def delete_location(location_id: int, db: Session = Depends(get_db)):
    try:
        result = deactivate_raw_material_location_in_session(db, location_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


@router.get("/inventory-lots", response_model=RawMaterialInventoryLotListOut)
def list_inventory_lots(
    raw_material_id: int | None = Query(None, ge=1),
    location_id: int | None = Query(None, ge=1),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return list_raw_material_inventory_lots_for_grid(
        db,
        raw_material_id=raw_material_id,
        location_id=location_id,
        q=q,
        page=page,
        size=size,
    )


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
    return list_raw_material_movements_for_grid(
        db,
        raw_material_id=raw_material_id,
        location_id=location_id,
        inventory_lot_id=inventory_lot_id,
        lot_no=lot_no,
        movement_type=movement_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
    )


@router.post("/inbound", response_model=RawMaterialMovementOut, status_code=status.HTTP_201_CREATED)
def inbound_raw_material(payload: RawMaterialInboundIn, db: Session = Depends(get_db)):
    try:
        result = inbound_raw_material_in_session(db, payload)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


@router.post("/transfer", response_model=RawMaterialMovementListOut, status_code=status.HTTP_201_CREATED)
def transfer_raw_material(payload: RawMaterialTransferIn, db: Session = Depends(get_db)):
    try:
        result = transfer_raw_material_in_session(db, payload)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


@router.post("/adjust", response_model=RawMaterialMovementOut, status_code=status.HTTP_201_CREATED)
def adjust_raw_material(
    payload: RawMaterialAdjustmentIn,
    direction: str = Query(...),
    db: Session = Depends(get_db),
):
    try:
        result = adjust_raw_material_in_session(db, payload=payload, direction=direction)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result
