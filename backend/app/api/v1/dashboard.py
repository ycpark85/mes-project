from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.inspection_result import InspectionResult
from app.models.inspection_schedule import InspectionSchedule
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.schemas.dashboard import (
    DashboardAlertOut,
    DashboardDefectRateTrendOut,
    DashboardFlowOut,
    DashboardInspectionSummaryOut,
    DashboardKpiOut,
    DashboardOutsourceSummaryOut,
    DashboardPeriodOut,
    DashboardQualitySummaryOut,
    DashboardStatusSegmentOut,
    DashboardSummaryOut,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _first_day_of_month(value: date) -> date:
    return date(value.year, value.month, 1)


def _safe_int(value) -> int:
    return int(value or 0)


def _safe_rate(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0

    return round((float(numerator) / float(denominator)) * 100, 1)


def _build_segment(
    key: str,
    label: str,
    count: int,
    total: int,
    color: str,
) -> DashboardStatusSegmentOut:
    return DashboardStatusSegmentOut(
        key=key,
        label=label,
        count=count,
        percent=_safe_rate(count, total),
        color=color,
    )


def _count_scalar(db: Session, stmt) -> int:
    return _safe_int(db.execute(stmt).scalar_one())


@router.get("/summary", response_model=DashboardSummaryOut)
def get_dashboard_summary(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    today = date.today()

    from_date = from_date or _first_day_of_month(today)
    to_date = to_date or today

    if from_date > to_date:
        raise HTTPException(
            status_code=400,
            detail="from_date must be less than or equal to to_date",
        )

    # ---------------------------------------------------------------------
    # 발주 / LOT
    # ---------------------------------------------------------------------
    order_base_filter = and_(
        OrderLine.is_active == True,  # noqa: E712
        OrderLine.status != "CANCELED",
        OrderLine.order_date >= from_date,
        OrderLine.order_date <= to_date,
    )

    total_order_count = _count_scalar(
        db,
        select(func.count())
        .select_from(OrderLine)
        .where(order_base_filter),
    )

    lot_waiting_count = _count_scalar(
        db,
        select(func.count())
        .select_from(OrderLine)
        .where(
            order_base_filter,
            OrderLine.status == "OPEN",
        ),
    )

    lot_created_count = _count_scalar(
        db,
        select(func.count())
        .select_from(Lot)
        .where(
            Lot.created_date >= from_date,
            Lot.created_date <= to_date,
        ),
    )

    # ---------------------------------------------------------------------
    # 외주
    # ---------------------------------------------------------------------
    outsource_base_filter = and_(
        OutsourceWorkInstruction.instruction_date >= from_date,
        OutsourceWorkInstruction.instruction_date <= to_date,
    )

    outsource_status_rows = (
        db.execute(
            select(
                OutsourceWorkGroup.status,
                func.count(OutsourceWorkGroup.outsource_work_group_id),
            )
            .join(
                OutsourceWorkInstruction,
                OutsourceWorkInstruction.outsource_work_instruction_id
                == OutsourceWorkGroup.outsource_work_instruction_id,
            )
            .where(outsource_base_filter)
            .group_by(OutsourceWorkGroup.status)
        )
        .all()
    )

    outsource_status_counts: dict[str, int] = {}

    for status, count in outsource_status_rows:
        key = status or "INSTRUCTION_CREATED"
        outsource_status_counts[key] = _safe_int(count)

    outsource_instruction_created_count = outsource_status_counts.get(
        "INSTRUCTION_CREATED",
        0,
    )
    outsource_vendor_received_count = outsource_status_counts.get(
        "VENDOR_RECEIVED",
        0,
    )
    outsource_work_done_count = outsource_status_counts.get(
        "WORK_DONE",
        0,
    )
    outsource_shipped_count = outsource_status_counts.get(
        "SHIPPED",
        0,
    )

    outsource_total_count = sum(outsource_status_counts.values())

    outsource_done_count = (
        outsource_work_done_count
        + outsource_shipped_count
    )

    outsource_in_progress_count = (
        outsource_instruction_created_count
        + outsource_vendor_received_count
    )

    outsource_segments = [
        _build_segment(
            "INSTRUCTION_CREATED",
            "지시등록",
            outsource_instruction_created_count,
            outsource_total_count,
            "#2563EB",
        ),
        _build_segment(
            "VENDOR_RECEIVED",
            "입고",
            outsource_vendor_received_count,
            outsource_total_count,
            "#93C5FD",
        ),
        _build_segment(
            "WORK_DONE",
            "작업완료",
            outsource_work_done_count,
            outsource_total_count,
            "#65A30D",
        ),
        _build_segment(
            "SHIPPED",
            "출고완료",
            outsource_shipped_count,
            outsource_total_count,
            "#0F766E",
        ),
    ]

    outsource = DashboardOutsourceSummaryOut(
        total_count=outsource_total_count,
        instruction_created_count=outsource_instruction_created_count,
        vendor_received_count=outsource_vendor_received_count,
        work_done_count=outsource_work_done_count,
        shipped_count=outsource_shipped_count,
        work_done_rate=_safe_rate(
            outsource_done_count,
            outsource_total_count,
        ),
        shipped_rate=_safe_rate(
            outsource_shipped_count,
            outsource_total_count,
        ),
        segments=outsource_segments,
    )

    # ---------------------------------------------------------------------
    # 검수
    # ---------------------------------------------------------------------
    inspection_base_filter = and_(
        InspectionSchedule.status != "CANCELED",
        InspectionSchedule.inspection_date >= from_date,
        InspectionSchedule.inspection_date <= to_date,
    )

    inspection_status_rows = (
        db.execute(
            select(
                InspectionSchedule.status,
                func.count(InspectionSchedule.inspection_schedule_id),
            )
            .where(inspection_base_filter)
            .group_by(InspectionSchedule.status)
        )
        .all()
    )

    inspection_status_counts = {
        status: _safe_int(count)
        for status, count in inspection_status_rows
    }

    inspection_waiting_count = inspection_status_counts.get("WAITING", 0)
    inspection_received_count = inspection_status_counts.get("RECEIVED", 0)
    inspection_in_progress_count = inspection_status_counts.get("IN_PROGRESS", 0)
    inspection_partial_done_count = inspection_status_counts.get("PARTIAL_DONE", 0)
    inspection_done_count = inspection_status_counts.get("DONE", 0)

    inspection_total_count = sum(inspection_status_counts.values())

    inspection_segments = [
        _build_segment(
            "WAITING",
            "대기",
            inspection_waiting_count,
            inspection_total_count,
            "#6B7280",
        ),
        _build_segment(
            "RECEIVED",
            "입고완료",
            inspection_received_count,
            inspection_total_count,
            "#93C5FD",
        ),
        _build_segment(
            "IN_PROGRESS",
            "진행중",
            inspection_in_progress_count,
            inspection_total_count,
            "#FBBF24",
        ),
        _build_segment(
            "PARTIAL_DONE",
            "부분완료",
            inspection_partial_done_count,
            inspection_total_count,
            "#8B5CF6",
        ),
        _build_segment(
            "DONE",
            "완료",
            inspection_done_count,
            inspection_total_count,
            "#65A30D",
        ),
    ]

    inspection = DashboardInspectionSummaryOut(
        total_count=inspection_total_count,
        waiting_count=inspection_waiting_count,
        received_count=inspection_received_count,
        in_progress_count=inspection_in_progress_count,
        partial_done_count=inspection_partial_done_count,
        done_count=inspection_done_count,
        done_rate=_safe_rate(
            inspection_done_count,
            inspection_total_count,
        ),
        segments=inspection_segments,
    )

    # ---------------------------------------------------------------------
    # 품질
    # ---------------------------------------------------------------------
    quality_row = (
        db.execute(
            select(
                func.coalesce(func.sum(InspectionResult.inspected_qty), 0),
                func.coalesce(func.sum(InspectionResult.good_qty), 0),
                func.coalesce(func.sum(InspectionResult.defect_qty), 0),
                func.coalesce(func.sum(InspectionResult.defect_ship_qty), 0),
            )
            .join(
                InspectionSchedule,
                InspectionSchedule.inspection_schedule_id
                == InspectionResult.inspection_schedule_id,
            )
            .where(inspection_base_filter)
        )
        .one()
    )

    inspected_qty = _safe_int(quality_row[0])
    good_qty = _safe_int(quality_row[1])
    defect_qty = _safe_int(quality_row[2])
    defect_ship_qty = _safe_int(quality_row[3])

    quality = DashboardQualitySummaryOut(
        inspected_qty=inspected_qty,
        good_qty=good_qty,
        defect_qty=defect_qty,
        defect_ship_qty=defect_ship_qty,
        good_rate=_safe_rate(good_qty, inspected_qty),
        defect_rate=_safe_rate(defect_qty, inspected_qty),
        defect_ship_rate=_safe_rate(defect_ship_qty, inspected_qty),
    )

    # ---------------------------------------------------------------------
    # 불량률 추이
    # ---------------------------------------------------------------------
    trend_rows = (
        db.execute(
            select(
                InspectionSchedule.inspection_date,
                func.coalesce(func.sum(InspectionResult.inspected_qty), 0),
                func.coalesce(func.sum(InspectionResult.defect_qty), 0),
            )
            .join(
                InspectionResult,
                InspectionResult.inspection_schedule_id
                == InspectionSchedule.inspection_schedule_id,
            )
            .where(inspection_base_filter)
            .group_by(InspectionSchedule.inspection_date)
            .order_by(InspectionSchedule.inspection_date.asc())
        )
        .all()
    )

    trend_rows = trend_rows[-10:]

    defect_rate_trend = [
        DashboardDefectRateTrendOut(
            date=row_date,
            inspected_qty=_safe_int(row_inspected_qty),
            defect_qty=_safe_int(row_defect_qty),
            defect_rate=_safe_rate(
                _safe_int(row_defect_qty),
                _safe_int(row_inspected_qty),
            ),
        )
        for row_date, row_inspected_qty, row_defect_qty in trend_rows
    ]

    # ---------------------------------------------------------------------
    # 주의 필요 항목
    # ---------------------------------------------------------------------
    due_soon_to_date = today + timedelta(days=7)

    due_soon_lot_count = _count_scalar(
        db,
        select(func.count())
        .select_from(Lot)
        .where(
            Lot.due_date >= today,
            Lot.due_date <= due_soon_to_date,
            Lot.status.notin_(["DONE", "CANCELED"]),
        ),
    )

    outsource_delay_base_date = today - timedelta(days=7)

    outsource_delay_count = _count_scalar(
        db,
        select(func.count())
        .select_from(OutsourceWorkGroup)
        .join(
            OutsourceWorkInstruction,
            OutsourceWorkInstruction.outsource_work_instruction_id
            == OutsourceWorkGroup.outsource_work_instruction_id,
        )
        .where(
            OutsourceWorkInstruction.instruction_date <= outsource_delay_base_date,
            or_(
                OutsourceWorkGroup.status.is_(None),
                OutsourceWorkGroup.status.notin_(["WORK_DONE", "SHIPPED"]),
            ),
        ),
    )

    inspection_delay_count = _count_scalar(
        db,
        select(func.count())
        .select_from(InspectionSchedule)
        .where(
            InspectionSchedule.inspection_date < today,
            InspectionSchedule.status.notin_(["DONE", "CANCELED"]),
        ),
    )

    defect_lot_count = _count_scalar(
        db,
        select(func.count(func.distinct(InspectionSchedule.lot_id)))
        .select_from(InspectionResult)
        .join(
            InspectionSchedule,
            InspectionSchedule.inspection_schedule_id
            == InspectionResult.inspection_schedule_id,
        )
        .where(
            inspection_base_filter,
            InspectionResult.defect_qty > 0,
        ),
    )

    alerts = [
        DashboardAlertOut(
            key="DUE_SOON_LOT",
            title="납기 임박 LOT",
            description="7일 이내 납기 도래",
            count=due_soon_lot_count,
            color="#EF4444",
        ),
        DashboardAlertOut(
            key="OUTSOURCE_DELAY",
            title="외주 지연",
            description="지시 후 7일 초과 미완료 외주",
            count=outsource_delay_count,
            color="#F59E0B",
        ),
        DashboardAlertOut(
            key="INSPECTION_DELAY",
            title="검수 지연",
            description="검수 예정일 초과 항목",
            count=inspection_delay_count,
            color="#8B5CF6",
        ),
        DashboardAlertOut(
            key="DEFECT_LOT",
            title="불량 발생 LOT",
            description="불량이 발생한 LOT",
            count=defect_lot_count,
            color="#EF4444",
        ),
    ]

    # ---------------------------------------------------------------------
    # 흐름
    # ---------------------------------------------------------------------
    flow = DashboardFlowOut(
        order_count=total_order_count,
        lot_created_count=lot_created_count,
        outsource_instruction_count=outsource_total_count,
        outsource_done_count=outsource_done_count,
        inspection_done_count=inspection_done_count,
    )

    kpi = DashboardKpiOut(
        total_order_count=total_order_count,
        lot_waiting_count=lot_waiting_count,
        outsource_in_progress_count=outsource_in_progress_count,
        inspection_waiting_count=inspection_waiting_count,
        inspection_done_rate=inspection.done_rate,
        defect_rate=quality.defect_rate,
    )

    return DashboardSummaryOut(
        period=DashboardPeriodOut(
            from_date=from_date,
            to_date=to_date,
        ),
        kpi=kpi,
        outsource=outsource,
        inspection=inspection,
        flow=flow,
        alerts=alerts,
        quality=quality,
        defect_rate_trend=defect_rate_trend,
    )