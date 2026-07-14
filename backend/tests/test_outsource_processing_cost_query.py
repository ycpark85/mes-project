from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import BigInteger, create_engine, event
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.outsource_processing_cost_group import OutsourceProcessingCostGroup
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.models.partner import Partner
from app.models.product import Product
from app.models.routing_template import RoutingTemplate
from app.services.outsource_processing_cost_common import (
    normalize_month,
    normalize_process_type,
)
from app.services.outsource_processing_cost_group_query import (
    list_outsource_processing_cost_groups,
)
from app.services.outsource_processing_cost_target_query import (
    list_outsource_processing_cost_targets,
)


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, compiler, **kw):
    return "INTEGER"


TEST_TABLE_NAMES = [
    "partner",
    "routing_template",
    "product",
    "order_line",
    "lot",
    "outsource_work_instruction",
    "outsource_work_group",
    "outsource_work_group_item",
    "outsource_processing_cost_group",
    "outsource_processing_cost_allocation",
    "outsource_processing_cost_work_group",
]


class OutsourceProcessingCostQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        tables = [Base.metadata.tables[name] for name in TEST_TABLE_NAMES]
        Base.metadata.create_all(self.engine, tables=tables)

        SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_list_outsource_processing_cost_groups_returns_empty_summary(self) -> None:
        result = list_outsource_processing_cost_groups(self.db)

        self.assertEqual([], result.items)
        self.assertEqual(0, result.total_count)
        self.assertEqual(0, result.standard_total)
        self.assertEqual(0, result.actual_total)
        self.assertEqual(0, result.difference_total)
        self.assertEqual(0, result.unclosed_count)

    def test_list_outsource_processing_cost_groups_excludes_canceled_by_default(self) -> None:
        self._add_cost_group(1, status="DRAFT")
        self._add_cost_group(2, status="CANCELED")

        result = list_outsource_processing_cost_groups(self.db)

        self.assertEqual(["OPC-CUT-202607-0001"], [item.cost_group_no for item in result.items])

    def test_list_outsource_processing_cost_groups_can_filter_canceled(self) -> None:
        self._add_cost_group(1, status="DRAFT")
        self._add_cost_group(2, status="CANCELED")

        result = list_outsource_processing_cost_groups(self.db, status="CANCELED")

        self.assertEqual(["OPC-CUT-202607-0002"], [item.cost_group_no for item in result.items])

    def test_list_outsource_processing_cost_targets_returns_allocation_preview(self) -> None:
        self._seed_target()

        result = list_outsource_processing_cost_targets(self.db, process_type="CUT")

        self.assertEqual(1, len(result.items))
        item = result.items[0]
        self.assertEqual("WG:1", item.target_key)
        self.assertEqual("OWI-001", item.instruction_no)
        self.assertEqual("Vendor", item.partner_name)
        self.assertEqual(Decimal("2.000000"), item.allocation_basis_value)
        self.assertEqual(1, len(item.allocations))
        self.assertEqual(Decimal("2.000000"), item.allocations[0].basis_value)

    def test_list_outsource_processing_cost_targets_uses_bounded_queries(self) -> None:
        self._seed_target()
        self.db.add_all(
            [
                OutsourceWorkGroup(
                    outsource_work_group_id=2,
                    outsource_work_instruction_id=1,
                    group_seq="G-002",
                    process_type="CUT",
                    is_bundle=False,
                    sheet_qty=2,
                    sheet_cut_count=1,
                    representative_lot_id=1,
                ),
                OutsourceWorkGroupItem(
                    outsource_work_group_item_id=2,
                    outsource_work_group_id=2,
                    lot_id=1,
                    cuts_per_sheet=1,
                    expected_output_qty=2,
                ),
            ]
        )
        self.db.commit()
        statement_count = 0

        def count_statement(*_args) -> None:
            nonlocal statement_count
            statement_count += 1

        event.listen(self.engine, "before_cursor_execute", count_statement)
        try:
            result = list_outsource_processing_cost_targets(
                self.db,
                process_type="CUT",
            )
        finally:
            event.remove(self.engine, "before_cursor_execute", count_statement)

        self.assertEqual(2, len(result.items))
        self.assertLessEqual(statement_count, 3)

    def test_normalize_process_type_rejects_invalid_value(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            normalize_process_type("BAD")

        self.assertEqual(409, ctx.exception.status_code)

    def test_normalize_month_uses_first_day_of_month(self) -> None:
        self.assertEqual(date(2026, 7, 1), normalize_month(date(2026, 7, 8)))

    def _add_cost_group(self, cost_group_id: int, *, status: str) -> None:
        self.db.add(
            OutsourceProcessingCostGroup(
                outsource_processing_cost_group_id=cost_group_id,
                cost_group_no=f"OPC-CUT-202607-{cost_group_id:04d}",
                settlement_month=date(2026, 7, 1),
                process_type="CUT",
                status=status,
                standard_amount=Decimal("1000"),
                actual_amount=Decimal("1000"),
            )
        )
        self.db.commit()

    def _seed_target(self) -> None:
        self.db.add_all(
            [
                Partner(
                    partner_id=1,
                    partner_type="CUSTOMER",
                    name="Customer",
                    business_no="C-001",
                    is_active=True,
                ),
                Partner(
                    partner_id=2,
                    partner_type="VENDOR",
                    name="Vendor",
                    business_no="V-001",
                    is_active=True,
                ),
                RoutingTemplate(
                    routing_template_id=1,
                    template_code="BLANK",
                    template_name="Blank",
                    is_active=True,
                ),
                Product(
                    product_id=1,
                    product_code="P-001",
                    product_name="Product",
                    uom="EA",
                    drawing_id=1,
                    routing_template_id=1,
                    panel_width_mm=1000,
                    panel_length_mm=1000,
                    is_active=True,
                ),
                OrderLine(
                    order_line_id=1,
                    order_no="SO-001",
                    line_no=1,
                    partner_id=1,
                    product_id=1,
                    order_date=date(2026, 7, 1),
                    due_date=date(2026, 7, 10),
                    order_qty=2,
                    uom="EA",
                    status="OPEN",
                    is_active=True,
                ),
                Lot(
                    lot_id=1,
                    lot_no="LOT-001",
                    order_line_id=1,
                    product_id=1,
                    lot_qty=2,
                    uom="EA",
                    created_date=date(2026, 7, 1),
                    due_date=date(2026, 7, 10),
                    status="WAITING",
                ),
                OutsourceWorkInstruction(
                    outsource_work_instruction_id=1,
                    instruction_no="OWI-001",
                    instruction_date=date(2026, 7, 2),
                    process_type="CUT",
                    partner_id=2,
                    is_bundle=False,
                ),
                OutsourceWorkGroup(
                    outsource_work_group_id=1,
                    outsource_work_instruction_id=1,
                    group_seq="G-001",
                    process_type="CUT",
                    is_bundle=False,
                    sheet_qty=2,
                    sheet_cut_count=1,
                    representative_lot_id=1,
                ),
                OutsourceWorkGroupItem(
                    outsource_work_group_item_id=1,
                    outsource_work_group_id=1,
                    lot_id=1,
                    cuts_per_sheet=1,
                    expected_output_qty=2,
                ),
            ]
        )
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
