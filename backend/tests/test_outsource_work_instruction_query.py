from __future__ import annotations

import unittest
from datetime import date

from fastapi import HTTPException
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.models.outsource_work_instruction_file import OutsourceWorkInstructionFile
from app.models.outsource_work_instruction_item import OutsourceWorkInstructionItem
from app.models.partner import Partner
from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.routing_template import RoutingTemplate
from app.services.outsource_work_instruction_query import (
    build_work_instruction_out,
    get_work_group_detail,
    list_candidate_lots,
    list_work_groups,
)


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, compiler, **kw):
    return "INTEGER"


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(_type, compiler, **kw):
    return "JSON"


TEST_TABLE_NAMES = [
    "partner",
    "routing_template",
    "product",
    "product_inventory",
    "order_line",
    "lot",
    "outsource_purchase_order",
    "outsource_purchase_order_item",
    "outsource_purchase_order_group",
    "outsource_work_instruction",
    "outsource_work_instruction_item",
    "outsource_work_instruction_file",
    "outsource_work_group",
    "outsource_work_group_item",
    "inspection_schedule",
    "raw_material",
    "raw_material_location",
    "raw_material_inventory_lot",
    "raw_material_inventory_movement",
    "outsource_work_group_raw_material_allocation",
    "self_use_sheet_job",
    "self_use_sheet_raw_material_allocation",
    "self_use_sheet_inventory_lot",
    "self_use_sheet_inventory_balance",
    "self_use_sheet_inventory_movement",
    "outsource_work_group_self_use_sheet_allocation",
    "outsource_work_group_self_use_sheet_source_snapshot",
]


class OutsourceWorkInstructionQueryTests(unittest.TestCase):
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

    def test_list_candidate_lots_excludes_registered_and_inspection_only_lots(self) -> None:
        result = list_candidate_lots(self.db)

        self.assertEqual([2], [item.lot_id for item in result.items])

        item = result.items[0]
        self.assertEqual("LOT-002", item.lot_no)
        self.assertEqual(["CUT", "PRINT"], item.available_process_types)
        self.assertEqual(25, item.current_stock_qty)
        self.assertEqual("Customer", item.customer_partner_name)

    def test_list_candidate_lots_filters_by_process_type_and_query(self) -> None:
        print_result = list_candidate_lots(self.db, process_type="PRINT", q="P-002")
        cut_result = list_candidate_lots(self.db, process_type="CUT", q="P-001")

        self.assertEqual([2], [item.lot_id for item in print_result.items])
        self.assertEqual([], cut_result.items)

    def test_list_candidate_lots_requires_full_order_number(self) -> None:
        partial_result = list_candidate_lots(self.db, q="SO-")
        exact_result = list_candidate_lots(self.db, q=" so-002 ")

        self.assertEqual([], partial_result.items)
        self.assertEqual([2], [item.lot_id for item in exact_result.items])

    def test_list_candidate_lots_rejects_invalid_process_type(self) -> None:
        with self.assertRaises(HTTPException) as error:
            list_candidate_lots(self.db, process_type="DIECUT")

        self.assertEqual(409, error.exception.status_code)
        self.assertEqual("Invalid process_type", error.exception.detail)

    def test_list_work_groups_returns_summary_items(self) -> None:
        result = list_work_groups(self.db, process_type="CUT", q="LOT-001")

        self.assertEqual(1, result.total_count)
        self.assertEqual(1, len(result.items))

        item = result.items[0]
        self.assertEqual(1, item.outsource_work_group_id)
        self.assertEqual("REGISTERED", item.status)
        self.assertEqual("\uc9c0\uc2dc\ub4f1\ub85d", item.status_name)
        self.assertEqual("LOT-001", item.lot_nos_text)
        self.assertTrue(item.can_cancel)
        self.assertTrue(item.can_update)

    def test_get_work_group_detail_returns_lots_and_files(self) -> None:
        result = get_work_group_detail(self.db, 1)

        self.assertEqual("OWI-001", result.instruction_no)
        self.assertEqual("LOT-001", result.representative_lot_no)
        self.assertEqual(["LOT-001"], [lot.lot_no for lot in result.lots])
        self.assertEqual(["plate.pdf", "cutting.pdf"], [file.file_name for file in result.files])

    def test_build_work_instruction_out_returns_items_and_files(self) -> None:
        instruction = self.db.get(OutsourceWorkInstruction, 1)

        result = build_work_instruction_out(self.db, instruction)

        self.assertEqual("OWI-001", result.instruction_no)
        self.assertEqual("CUT", result.process_type)
        self.assertEqual([1, 2], [item.outsource_work_instruction_item_id for item in result.items])
        self.assertEqual(["LOT-001", "LOT-002"], [item.lot_no for item in result.items])
        self.assertEqual(["SO-001", "SO-002"], [item.order_no for item in result.items])
        self.assertEqual([1, 2], [file.outsource_work_instruction_file_id for file in result.files])
        self.assertEqual(["plate.pdf", "cutting.pdf"], [file.file_name for file in result.files])

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
                RoutingTemplate(
                    routing_template_id=1,
                    template_code="BLANK",
                    template_name="\ubb34\uc9c0",
                    is_active=True,
                ),
                RoutingTemplate(
                    routing_template_id=2,
                    template_code="PRINT",
                    template_name="\uc778\uc1c4",
                    is_active=True,
                ),
                RoutingTemplate(
                    routing_template_id=3,
                    template_code="INSPECTION",
                    template_name="\uac80\uc218\ub9cc\uc9c4\ud589",
                    is_active=True,
                ),
                Product(
                    product_id=1,
                    product_code="P-001",
                    product_name="Blank Product",
                    uom="EA",
                    drawing_id=1,
                    routing_template_id=1,
                    is_active=True,
                ),
                Product(
                    product_id=2,
                    product_code="P-002",
                    product_name="Print Product",
                    uom="EA",
                    drawing_id=2,
                    routing_template_id=2,
                    panel_width_mm=100,
                    panel_length_mm=200,
                    product_spec="Spec",
                    cut_qty_per_panel=4,
                    is_active=True,
                ),
                Product(
                    product_id=3,
                    product_code="P-003",
                    product_name="Inspection Product",
                    uom="EA",
                    drawing_id=3,
                    routing_template_id=3,
                    is_active=True,
                ),
                ProductInventory(
                    product_inventory_id=2,
                    product_id=2,
                    current_qty=25,
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
                    order_qty=200,
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
                    order_qty=300,
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
                    created_date=date(2026, 1, 3),
                    due_date=date(2026, 1, 10),
                    status="WAITING",
                ),
                Lot(
                    lot_id=2,
                    lot_no="LOT-002",
                    order_line_id=2,
                    product_id=2,
                    lot_qty=200,
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
                    lot_qty=300,
                    uom="EA",
                    created_date=date(2026, 1, 1),
                    due_date=date(2026, 1, 10),
                    status="WAITING",
                ),
                OutsourceWorkInstruction(
                    outsource_work_instruction_id=1,
                    instruction_no="OWI-001",
                    instruction_date=date(2026, 1, 4),
                    process_type="CUT",
                    partner_id=2,
                    is_bundle=False,
                ),
                OutsourceWorkInstructionItem(
                    outsource_work_instruction_item_id=1,
                    outsource_work_instruction_id=1,
                    lot_id=1,
                    process_type="CUT",
                    is_active=True,
                ),
                OutsourceWorkInstructionItem(
                    outsource_work_instruction_item_id=2,
                    outsource_work_instruction_id=1,
                    lot_id=2,
                    process_type="CUT",
                    is_active=True,
                ),
                OutsourceWorkInstructionFile(
                    outsource_work_instruction_file_id=1,
                    outsource_work_instruction_id=1,
                    file_name="plate.pdf",
                    file_path="/tmp/plate.pdf",
                    content_type="application/pdf",
                ),
                OutsourceWorkInstructionFile(
                    outsource_work_instruction_file_id=2,
                    outsource_work_instruction_id=1,
                    file_name="cutting.pdf",
                    file_path="/tmp/cutting.pdf",
                    content_type="application/pdf",
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
                OutsourceWorkGroupItem(
                    outsource_work_group_item_id=1,
                    outsource_work_group_id=1,
                    lot_id=1,
                    cuts_per_sheet=1,
                    expected_output_qty=100,
                ),
            ]
        )
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
