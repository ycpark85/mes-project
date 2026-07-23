from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.models.partner import Partner
from app.models.product import Product


@dataclass(frozen=True)
class WorkGroupUsageContext:
    product_display: str
    lot_display: str
    partner_display: str
    work_instruction_no: str
    work_group_seq: str


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _summarize(values: list[str], suffix: str) -> str:
    unique_values = _unique(values)
    if not unique_values:
        return "-"
    if len(unique_values) == 1:
        return unique_values[0]
    return f"{unique_values[0]} 외 {len(unique_values) - 1}{suffix}"


def load_work_group_usage_contexts(
    db: Session,
    work_group_ids: set[int],
) -> dict[int, WorkGroupUsageContext]:
    if not work_group_ids:
        return {}

    rows = db.execute(
        select(
            OutsourceWorkGroup.outsource_work_group_id,
            OutsourceWorkGroup.group_seq,
            OutsourceWorkInstruction.instruction_no,
            OutsourceWorkGroupItem.outsource_work_group_item_id,
            Product.product_name,
            Lot.lot_no,
            Partner.name.label("partner_name"),
        )
        .join(
            OutsourceWorkInstruction,
            OutsourceWorkInstruction.outsource_work_instruction_id
            == OutsourceWorkGroup.outsource_work_instruction_id,
        )
        .join(
            OutsourceWorkGroupItem,
            OutsourceWorkGroupItem.outsource_work_group_id
            == OutsourceWorkGroup.outsource_work_group_id,
        )
        .join(Lot, Lot.lot_id == OutsourceWorkGroupItem.lot_id)
        .join(Product, Product.product_id == Lot.product_id)
        .join(OrderLine, OrderLine.order_line_id == Lot.order_line_id)
        .join(Partner, Partner.partner_id == OrderLine.partner_id)
        .where(OutsourceWorkGroup.outsource_work_group_id.in_(work_group_ids))
        .order_by(
            OutsourceWorkGroup.outsource_work_group_id.asc(),
            OutsourceWorkGroupItem.outsource_work_group_item_id.asc(),
        )
    ).all()

    grouped: dict[int, dict[str, object]] = {}
    for row in rows:
        group_id = int(row.outsource_work_group_id)
        item = grouped.setdefault(
            group_id,
            {
                "products": [],
                "lots": [],
                "partners": [],
                "instruction_no": row.instruction_no,
                "group_seq": row.group_seq,
            },
        )
        item["products"].append(row.product_name)
        item["lots"].append(row.lot_no)
        item["partners"].append(row.partner_name)

    return {
        group_id: WorkGroupUsageContext(
            product_display=_summarize(item["products"], "건"),
            lot_display=_summarize(item["lots"], "건"),
            partner_display=_summarize(item["partners"], "곳"),
            work_instruction_no=str(item["instruction_no"]),
            work_group_seq=str(item["group_seq"]),
        )
        for group_id, item in grouped.items()
    }
