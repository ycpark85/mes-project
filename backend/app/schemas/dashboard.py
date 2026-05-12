from __future__ import annotations

from datetime import date
from typing import List

from pydantic import BaseModel, Field


class DashboardPeriodOut(BaseModel):
    from_date: date
    to_date: date


class DashboardKpiOut(BaseModel):
    total_order_count: int = 0
    lot_waiting_count: int = 0
    outsource_in_progress_count: int = 0
    inspection_waiting_count: int = 0
    inspection_done_rate: float = 0
    defect_rate: float = 0


class DashboardStatusSegmentOut(BaseModel):
    key: str
    label: str
    count: int = 0
    percent: float = 0
    color: str = "#CBD5E1"


class DashboardOutsourceSummaryOut(BaseModel):
    total_count: int = 0
    instruction_created_count: int = 0
    vendor_received_count: int = 0
    work_done_count: int = 0
    shipped_count: int = 0
    work_done_rate: float = 0
    shipped_rate: float = 0
    segments: List[DashboardStatusSegmentOut] = Field(default_factory=list)


class DashboardInspectionSummaryOut(BaseModel):
    total_count: int = 0
    waiting_count: int = 0
    received_count: int = 0
    in_progress_count: int = 0
    partial_done_count: int = 0
    done_count: int = 0
    done_rate: float = 0
    segments: List[DashboardStatusSegmentOut] = Field(default_factory=list)


class DashboardFlowOut(BaseModel):
    order_count: int = 0
    lot_created_count: int = 0
    outsource_instruction_count: int = 0
    outsource_done_count: int = 0
    inspection_done_count: int = 0


class DashboardAlertOut(BaseModel):
    key: str
    title: str
    description: str
    count: int = 0
    color: str = "#EF4444"


class DashboardQualitySummaryOut(BaseModel):
    inspected_qty: int = 0
    good_qty: int = 0
    defect_qty: int = 0
    defect_ship_qty: int = 0
    good_rate: float = 0
    defect_rate: float = 0
    defect_ship_rate: float = 0


class DashboardDefectRateTrendOut(BaseModel):
    date: date
    inspected_qty: int = 0
    defect_qty: int = 0
    defect_rate: float = 0


class DashboardSummaryOut(BaseModel):
    period: DashboardPeriodOut
    kpi: DashboardKpiOut
    outsource: DashboardOutsourceSummaryOut
    inspection: DashboardInspectionSummaryOut
    flow: DashboardFlowOut
    alerts: List[DashboardAlertOut] = Field(default_factory=list)
    quality: DashboardQualitySummaryOut
    defect_rate_trend: List[DashboardDefectRateTrendOut] = Field(default_factory=list)