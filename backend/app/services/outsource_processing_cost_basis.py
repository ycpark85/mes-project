from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lot import Lot
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.product import Product


def get_work_group_item_rows(
    db: Session,
    work_group_id: int,
) -> list[tuple[OutsourceWorkGroupItem, Lot, Product]]:
    return (
        db.execute(
            select(OutsourceWorkGroupItem, Lot, Product)
            .join(Lot, Lot.lot_id == OutsourceWorkGroupItem.lot_id)
            .join(Product, Product.product_id == Lot.product_id)
            .where(OutsourceWorkGroupItem.outsource_work_group_id == work_group_id)
            .order_by(
                Lot.lot_no.asc(),
                OutsourceWorkGroupItem.outsource_work_group_item_id.asc(),
            )
        )
        .all()
    )


def resolve_instruction_output_qty(
    work_group: OutsourceWorkGroup,
    group_item: OutsourceWorkGroupItem,
    lot: Lot,
) -> int:
    if group_item.expected_output_qty is not None:
        return int(group_item.expected_output_qty)

    if work_group.sheet_qty is not None and group_item.cuts_per_sheet is not None:
        return int(work_group.sheet_qty) * int(group_item.cuts_per_sheet)

    return int(lot.lot_qty)


def calculate_area_basis(product: Product, output_qty: int | None) -> Decimal:
    if not product.panel_width_mm or not product.panel_length_mm or not output_qty:
        return Decimal("0")

    return (
        Decimal(product.panel_width_mm)
        * Decimal(product.panel_length_mm)
        * Decimal(output_qty)
        / Decimal("1000000")
    ).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
