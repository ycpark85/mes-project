from __future__ import annotations

import unittest
from datetime import date

from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.drawing import Drawing
from app.models.inspection_schedule import InspectionSchedule
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.models.outsource_work_instruction_file import OutsourceWorkInstructionFile
from app.models.partner import Partner
from app.models.product import Product
from app.models.routing_template import RoutingTemplate
from app.services.inspection_work_instruction_query import (
    list_inspection_schedule_items,
    list_inspection_work_instruction_targets,
)


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, compiler, **kw):
    return "INTEGER"


TEST_TABLE_NAMES = [
    "partner",
    "drawing",
    "routing_template",
    "product",
    "order_line",
    "lot",
    "outsource_work_instruction",
    "outsource_work_instruction_file",
    "outsource_work_group",
    "outsource_work_group_item",
    "inspection_schedule",
]


class InspectionWorkInstructionQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        tables = [Base.metadata.tables[name] for name in TEST_TABLE_NAMES]
        Base.metadata.create_all(self.engine, tables=tables)

        SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()
        self._seed_data()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_list_targets_excludes_canceled_outsource_work_group(self) -> None:
        inspection_schedule = self.db.get(InspectionSchedule, 1)
        inspection_schedule.status = "CANCELED"
        self.db.flush()

        result = list_inspection_work_instruction_targets(self.db)

        lot_nos = [item.lot_no for item in result.items]

        self.assertIn("LOT-001", lot_nos)
        self.assertIn("LOT-003", lot_nos)
        self.assertNotIn("LOT-002", lot_nos)

    def test_list_schedule_items_returns_outsource_display_fields(self) -> None:
        result = list_inspection_schedule_items(self.db)

        self.assertEqual(1, len(result))

        item = result[0]
        self.assertEqual(1, item.inspection_schedule_id)
        self.assertEqual("LOT-001", item.lot_no)
        self.assertEqual(1, item.outsource_work_group_id)
        self.assertEqual("plate.pdf", item.plate_data_file_name)
        self.assertEqual("C:/plate.pdf", item.plate_data_file_path)
        self.assertEqual("D-001", item.drawing_no)
        self.assertEqual("\uc678\uc8fc \uc785\uace0\ub300\uae30", item.diecut_status)

    def _seed_data(self) -> None:
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
                Drawing(
                    drawing_id=1,
                    drawing_no="D-001",
                    is_active=True,
                ),
                Drawing(
                    drawing_id=2,
                    drawing_no="D-002",
                    is_active=True,
                ),
                Drawing(
                    drawing_id=3,
                    drawing_no="D-003",
                    is_active=True,
                ),
                RoutingTemplate(
                    routing_template_id=1,
                    template_code="CUT",
                    template_name="CUT",
                    is_active=True,
                ),
                RoutingTemplate(
                    routing_template_id=2,
                    template_code="INSPECTION_ONLY",
                    template_name="\uac80\uc218\ub9cc\uc9c4\ud589",
                    is_active=True,
                ),
                Product(
                    product_id=1,
                    product_code="P-001",
                    product_name="Product 1",
                    uom="EA",
                    drawing_id=1,
                    routing_template_id=1,
                    is_active=True,
                ),
                Product(
                    product_id=2,
                    product_code="P-002",
                    product_name="Product 2",
                    uom="EA",
                    drawing_id=2,
                    routing_template_id=1,
                    is_active=True,
                ),
                Product(
                    product_id=3,
                    product_code="P-003",
                    product_name="Product 3",
                    uom="EA",
                    drawing_id=3,
                    routing_template_id=2,
                    is_active=True,
                ),
                OrderLine(
                    order_line_id=1,
                    order_no="SO-001",
                    line_no=1,
                    partner_id=1,
                    product_id=1,
                    order_date=date(2026, 1, 1),
                    due_date=date(2026, 1, 10),
                    order_qty=100,
                    uom="EA",
                    status="OPEN",
                    is_active=True,
                ),
                OrderLine(
                    order_line_id=2,
                    order_no="SO-002",
                    line_no=1,
                    partner_id=1,
                    product_id=2,
                    order_date=date(2026, 1, 1),
                    due_date=date(2026, 1, 10),
                    order_qty=100,
                    uom="EA",
                    status="OPEN",
                    is_active=True,
                ),
                OrderLine(
                    order_line_id=3,
                    order_no="SO-003",
                    line_no=1,
                    partner_id=1,
                    product_id=3,
                    order_date=date(2026, 1, 1),
                    due_date=date(2026, 1, 10),
                    order_qty=100,
                    uom="EA",
                    status="OPEN",
                    is_active=True,
                ),
                Lot(
                    lot_id=1,
                    lot_no="LOT-001",
                    order_line_id=1,
                    product_id=1,
                    lot_qty=100,
                    uom="EA",
                    created_date=date(2026, 1, 2),
                    due_date=date(2026, 1, 10),
                    status="WAITING",
                ),
                Lot(
                    lot_id=2,
                    lot_no="LOT-002",
                    order_line_id=2,
                    product_id=2,
                    lot_qty=100,
                    uom="EA",
                    created_date=date(2026, 1, 2),
                    due_date=date(2026, 1, 10),
                    status="WAITING",
                ),
                Lot(
                    lot_id=3,
                    lot_no="LOT-003",
                    order_line_id=3,
                    product_id=3,
                    lot_qty=100,
                    uom="EA",
                    created_date=date(2026, 1, 2),
                    due_date=date(2026, 1, 10),
                    status="WAITING",
                ),
                OutsourceWorkInstruction(
                    outsource_work_instruction_id=1,
                    instruction_no="OWI-001",
                    instruction_date=date(2026, 1, 3),
                    process_type="CUT",
                    partner_id=2,
                    is_bundle=False,
                ),
                OutsourceWorkInstructionFile(
                    outsource_work_instruction_file_id=1,
                    outsource_work_instruction_id=1,
                    file_name="plate.pdf",
                    file_path="C:/plate.pdf",
                    content_type="application/pdf",
                ),
                OutsourceWorkInstruction(
                    outsource_work_instruction_id=2,
                    instruction_no="OWI-002",
                    instruction_date=date(2026, 1, 3),
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
                    sheet_qty=100,
                    sheet_cut_count=1,
                    status=None,
                    representative_lot_id=1,
                ),
                OutsourceWorkGroup(
                    outsource_work_group_id=2,
                    outsource_work_instruction_id=2,
                    group_seq="G-002",
                    process_type="CUT",
                    is_bundle=False,
                    sheet_qty=100,
                    sheet_cut_count=1,
                    status="CANCELED",
                    representative_lot_id=2,
                ),
                OutsourceWorkGroupItem(
                    outsource_work_group_item_id=1,
                    outsource_work_group_id=1,
                    lot_id=1,
                    cuts_per_sheet=1,
                    expected_output_qty=100,
                ),
                OutsourceWorkGroupItem(
                    outsource_work_group_item_id=2,
                    outsource_work_group_id=2,
                    lot_id=2,
                    cuts_per_sheet=1,
                    expected_output_qty=100,
                ),
                InspectionSchedule(
                    inspection_schedule_id=1,
                    lot_id=1,
                    outsource_work_group_id=1,
                    outsource_work_group_item_id=1,
                    inspection_date=date(2026, 1, 4),
                    status="WAITING",
                    day_seq=1,
                ),
            ]
        )
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
