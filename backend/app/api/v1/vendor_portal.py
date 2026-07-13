from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.user import User
from app.models.vendor_portal_audit_log import VendorPortalAuditLog
from app.models.vendor_user_access import VendorUserAccess
from app.schemas.outsource_work_instruction import (
    BohyunOutsourceGroupListOut,
    BohyunOutsourceGroupShipBatch,
)
from app.schemas.vendor_portal import VendorPortalBohyunWorkDone
import app.services.bohyun_outsource_service as bohyun_outsource_service


router = APIRouter(prefix="/vendor-portal", tags=["VendorPortal"])


class VendorPortalContext:
    def __init__(self, user: User, partner_id: int) -> None:
        self.user = user
        self.partner_id = partner_id


def require_bohyun_vendor_access(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VendorPortalContext:
    bohyun_partner_id = settings.VENDOR_PORTAL_BOHYUN_PARTNER_ID

    if bohyun_partner_id is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vendor portal Bohyun partner is not configured",
        )

    access = (
        db.execute(
            select(VendorUserAccess)
            .where(
                VendorUserAccess.user_id == current_user.user_id,
                VendorUserAccess.partner_id == bohyun_partner_id,
                VendorUserAccess.is_active.is_(True),
            )
            .limit(1)
        )
        .scalar_one_or_none()
    )

    if access is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor portal access is not allowed",
        )

    return VendorPortalContext(
        user=current_user,
        partner_id=bohyun_partner_id,
    )


@router.get("/bohyun-groups", response_model=BohyunOutsourceGroupListOut)
def get_vendor_bohyun_outsource_groups(
    request: Request,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    process_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
    context: VendorPortalContext = Depends(require_bohyun_vendor_access),
    db: Session = Depends(get_db),
):
    result = bohyun_outsource_service.list_bohyun_outsource_groups(
        db,
        date_from=date_from,
        date_to=date_to,
        process_type=process_type,
        status=status,
        q=q,
        include_processing_fee=True,
    )
    _write_vendor_audit_log(
        db,
        request=request,
        context=context,
        action_type="VIEW_LIST",
        outsource_work_group_id=None,
        before_status=None,
        after_status=None,
        remark=None,
    )
    db.commit()
    return result


@router.post("/bohyun-groups/{group_id}/inbound")
def inbound_vendor_bohyun_outsource_group(
    group_id: int,
    request: Request,
    context: VendorPortalContext = Depends(require_bohyun_vendor_access),
    db: Session = Depends(get_db),
):
    before_status = _get_work_group_status(db, group_id)
    bohyun_outsource_service.inbound_bohyun_outsource_group(db, group_id)
    after_status = _get_work_group_status(db, group_id)
    _write_vendor_audit_log(
        db,
        request=request,
        context=context,
        action_type="INBOUND",
        outsource_work_group_id=group_id,
        before_status=before_status,
        after_status=after_status,
        remark=None,
    )
    db.commit()
    return {"success": True}


@router.post("/bohyun-groups/{group_id}/work-done")
def complete_vendor_bohyun_outsource_group_work(
    group_id: int,
    payload: VendorPortalBohyunWorkDone,
    request: Request,
    context: VendorPortalContext = Depends(require_bohyun_vendor_access),
    db: Session = Depends(get_db),
):
    before_status = _get_work_group_status(db, group_id)
    bohyun_outsource_service.complete_bohyun_outsource_group_work(
        db,
        group_id,
        work_done_sheet_qty=payload.work_done_sheet_qty,
        outsource_processing_fee=payload.outsource_processing_fee,
        remark=payload.remark,
    )
    after_status = _get_work_group_status(db, group_id)
    _write_vendor_audit_log(
        db,
        request=request,
        context=context,
        action_type="WORK_DONE",
        outsource_work_group_id=group_id,
        before_status=before_status,
        after_status=after_status,
        remark=payload.remark,
    )
    db.commit()
    return {"success": True}


@router.post("/bohyun-groups/ship-batch")
def ship_vendor_bohyun_outsource_groups(
    payload: BohyunOutsourceGroupShipBatch,
    request: Request,
    context: VendorPortalContext = Depends(require_bohyun_vendor_access),
    db: Session = Depends(get_db),
):
    requested_group_ids = list(dict.fromkeys(payload.group_ids))
    before_statuses = {
        group_id: _get_work_group_status(db, group_id)
        for group_id in requested_group_ids
    }
    bohyun_outsource_service.ship_bohyun_outsource_groups(db, requested_group_ids)

    for group_id in requested_group_ids:
        _write_vendor_audit_log(
            db,
            request=request,
            context=context,
            action_type="SHIP",
            outsource_work_group_id=group_id,
            before_status=before_statuses.get(group_id),
            after_status=_get_work_group_status(db, group_id),
            remark=None,
        )

    db.commit()
    return {"success": True}


def _get_work_group_status(db: Session, group_id: int) -> str | None:
    return db.execute(
        select(OutsourceWorkGroup.status).where(
            OutsourceWorkGroup.outsource_work_group_id == group_id
        )
    ).scalar_one_or_none()


def _write_vendor_audit_log(
    db: Session,
    *,
    request: Request,
    context: VendorPortalContext,
    action_type: str,
    outsource_work_group_id: int | None,
    before_status: str | None,
    after_status: str | None,
    remark: str | None,
) -> None:
    user_agent = request.headers.get("user-agent")
    client_host = request.client.host if request.client else None

    db.add(
        VendorPortalAuditLog(
            user_id=context.user.user_id,
            partner_id=context.partner_id,
            outsource_work_group_id=outsource_work_group_id,
            action_type=action_type,
            before_status=before_status,
            after_status=after_status,
            request_ip=client_host,
            user_agent=user_agent,
            remark=remark,
        )
    )
