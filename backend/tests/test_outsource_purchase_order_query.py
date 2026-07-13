from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.outsource_purchase_order import OutsourcePurchaseOrder
from app.models.outsource_purchase_order_group import OutsourcePurchaseOrderGroup
from app.models.outsource_purchase_order_item import OutsourcePurchaseOrderItem
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.models.outsource_work_instruction_file import OutsourceWorkInstructionFile
from app.models.outsource_work_instruction_item import OutsourceWorkInstructionItem
from app.models.partner import Partner
from app.models.product import Product
from app.models.routing_template import RoutingTemplate
from app.services.outsource_purchase_order_query import (
    build_purchase_order_out,
    get_purchase_order_detail,
    list_purchase_order_targets,
    list_purchase_orders,
)


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(_type, compiler, **kw):
    return "JSON"


TEST_TABLE_NAMES = [
    "partner",
    "routing_template",
    "product",
    "order_line",
    "lot",
    "outsource_work_instruction",
    "outsource_work_instruction_item",
    "outsource_work_instruction_file",
    "outsource_work_group",
    "outsource_work_group_item",
    "outsource_purchase_order",
    "outsource_purchase_order_item",
    "outsource_purchase_order_group",
]


class OutsourcePurchaseOrderQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        tables = [Base.metadata.tables[name] for name in TEST_TABLE_NAMES]
        Base.metadata.create_all(self.engine, tables=tables)

        SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()
        self._seed_base_data()
        self._seed_purchase_orders()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_build_purchase_order_out_includes_partner_names_and_sorted_items(self) -> None:
        purchase_order = self.db.get(OutsourcePurchaseOrder, 1)

        result = build_purchase_order_out(self.db, purchase_order)

        self.assertEqual("OCUT-20260103-001", result.purchase_order_no)
        self.assertEqual("Vendor A", result.outsource_partner_name)
        self.assertEqual("Inbound B", result.inbound_partner_name)
        self.assertEqual([1, 2], [item.item_seq for item in result.items])
        self.assertEqual(["LOT-002", "LOT-001"], [item.lot_no for item in result.items])
        self.assertEqual(["SO-002", "SO-001"], [item.order_no for item in result.items])
        self.assertEqual(["Product 2", "Product 1"], [item.product_name for item in result.items])

    def test_get_purchase_order_detail_returns_detail(self) -> None:
        result = get_purchase_order_detail(self.db, 1)

        self.assertEqual(1, result.outsource_purchase_order_id)
        self.assertEqual("OCUT-20260103-001", result.purchase_order_no)
        self.assertEqual([1, 2], [item.item_seq for item in result.items])

    def test_get_purchase_order_detail_rejects_missing_order(self) -> None:
        with self.assertRaises(HTTPException) as error:
            get_purchase_order_detail(self.db, 999)

        self.assertEqual(404, error.exception.status_code)

    def test_list_purchase_orders_default_orders_by_date_and_id_desc(self) -> None:
        result = list_purchase_orders(self.db)

        self.assertEqual(3, result.total_count)
        self.assertEqual(1, result.page)
        self.assertEqual(100, result.size)
        self.assertEqual(
            [3, 2, 1],
            [item.outsource_purchase_order_id for item in result.items],
        )

    def test_list_purchase_orders_paginates_results(self) -> None:
        result = list_purchase_orders(self.db, page=2, size=1)

        self.assertEqual(3, result.total_count)
        self.assertEqual(2, result.page)
        self.assertEqual(1, result.size)
        self.assertEqual(
            [2],
            [item.outsource_purchase_order_id for item in result.items],
        )

    def test_list_purchase_orders_filters_by_date_process_and_query(self) -> None:
        result = list_purchase_orders(
            self.db,
            date_from=date(2026, 1, 4),
            date_to=date(2026, 1, 5),
            process_type="print",
            q="urgent",
        )

        self.assertEqual(1, len(result.items))
        self.assertEqual(2, result.items[0].outsource_purchase_order_id)
        self.assertEqual("PRINT", result.items[0].process_type)
        self.assertEqual("Vendor A", result.items[0].outsource_partner_name)

    def test_list_purchase_orders_filters_by_outsource_partner_name(self) -> None:
        result = list_purchase_orders(self.db, q="Vendor Search")

        self.assertEqual(
            [3],
            [item.outsource_purchase_order_id for item in result.items],
        )
        self.assertEqual(
            ["Vendor Search"],
            [item.outsource_partner_name for item in result.items],
        )

    def test_list_purchase_order_targets_excludes_already_ordered_groups(self) -> None:
        result = list_purchase_order_targets(self.db, process_type="cut")

        self.assertEqual(1, result.total_count)
        self.assertEqual(1, result.page)
        self.assertEqual(100, result.size)
        self.assertEqual([3], [item.lot_id for item in result.items])

        item = result.items[0]
        self.assertEqual("OWI-020", item.instruction_no)
        self.assertEqual("G-020", item.group_seq)
        self.assertEqual("Customer C", item.customer_partner_name)
        self.assertEqual("\ubcf4\ud604", item.inbound_partner_name)
        self.assertFalse(item.is_print_product)
        self.assertEqual(1, len(item.files))
        self.assertEqual("plate.pdf", item.files[0].file_name)

    def test_list_purchase_order_targets_paginates_by_work_group(self) -> None:
        self.db.add_all(
            [
                OutsourceWorkGroup(
                    outsource_work_group_id=22,
                    outsource_work_instruction_id=21,
                    group_seq="G-022",
                    process_type="CUT",
                    is_bundle=False,
                    sheet_qty=400,
                    sheet_cut_count=1,
                    status=None,
                    representative_lot_id=4,
                ),
                OutsourceWorkGroupItem(
                    outsource_work_group_item_id=22,
                    outsource_work_group_id=22,
                    lot_id=4,
                    cuts_per_sheet=1,
                    expected_output_qty=400,
                ),
            ]
        )
        self.db.commit()

        first_page = list_purchase_order_targets(self.db, process_type="cut", page=1, size=1)
        second_page = list_purchase_order_targets(self.db, process_type="cut", page=2, size=1)

        self.assertEqual(2, first_page.total_count)
        self.assertEqual(1, first_page.page)
        self.assertEqual(1, first_page.size)
        self.assertEqual([22], [item.outsource_work_group_id for item in first_page.items])

        self.assertEqual(2, second_page.total_count)
        self.assertEqual(2, second_page.page)
        self.assertEqual(1, second_page.size)
        self.assertEqual([20], [item.outsource_work_group_id for item in second_page.items])

    def _seed_base_data(self) -> None:
        self.db.add_all(
            [
                Partner(
                    partner_id=1,
                    partner_type="VENDOR",
                    name="Vendor A",
                    business_no="V-001",
                    is_active=True,
                ),
                Partner(
                    partner_id=2,
                    partner_type="VENDOR",
                    name="Inbound B",
                    business_no="V-002",
                    is_active=True,
                ),
                Partner(
                    partner_id=5,
                    partner_type="VENDOR",
                    name="Vendor Search",
                    business_no="V-005",
                    is_active=True,
                ),
                Partner(
                    partner_id=3,
                    partner_type="CUSTOMER",
                    name="Customer C",
                    business_no="C-001",
                    is_active=True,
                ),
                Partner(
                    partner_id=4,
                    partner_type="VENDOR",
                    name="\ucf54\ub9ac\uc544\ub77c\ubca8 \uc8fc\uc2dd\ud68c\uc0ac",
                    business_no="V-004",
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
                    template_code="BLANK",
                    template_name="\ubb34\uc9c0",
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
                    panel_width_mm=100,
                    panel_length_mm=200,
                    product_spec="Spec 3",
                    cut_qty_per_panel=4,
                    is_active=True,
                ),
                Product(
                    product_id=4,
                    product_code="P-004",
                    product_name="Product 4",
                    uom="EA",
                    drawing_id=4,
                    routing_template_id=2,
                    is_active=True,
                ),
                OrderLine(
                    order_line_id=1,
                    order_no="SO-001",
                    line_no=1,
                    partner_id=3,
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
                    partner_id=3,
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
                    partner_id=3,
                    product_id=3,
                    order_date=date(2026, 1, 1),
                    due_date=date(2026, 1, 10),
                    order_qty=300,
                    uom="EA",
                    status="OPEN",
                    is_active=True,
                ),
                OrderLine(
                    order_line_id=4,
                    order_no="SO-004",
                    line_no=1,
                    partner_id=3,
                    product_id=4,
                    order_date=date(2026, 1, 1),
                    due_date=date(2026, 1, 10),
                    order_qty=400,
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
                    created_date=date(2026, 1, 2),
                    due_date=date(2026, 1, 10),
                    status="WAITING",
                ),
                Lot(
                    lot_id=4,
                    lot_no="LOT-004",
                    order_line_id=4,
                    product_id=4,
                    lot_qty=400,
                    uom="EA",
                    created_date=date(2026, 1, 2),
                    due_date=date(2026, 1, 10),
                    status="WAITING",
                ),
                OutsourceWorkInstruction(
                    outsource_work_instruction_id=20,
                    instruction_no="OWI-020",
                    instruction_date=date(2026, 1, 5),
                    process_type="CUT",
                    partner_id=4,
                    is_bundle=False,
                    memo="target memo",
                ),
                OutsourceWorkInstruction(
                    outsource_work_instruction_id=21,
                    instruction_no="OWI-021",
                    instruction_date=date(2026, 1, 6),
                    process_type="CUT",
                    partner_id=4,
                    is_bundle=False,
                ),
                OutsourceWorkInstructionItem(
                    outsource_work_instruction_item_id=20,
                    outsource_work_instruction_id=20,
                    lot_id=3,
                    process_type="CUT",
                    is_active=True,
                ),
                OutsourceWorkInstructionItem(
                    outsource_work_instruction_item_id=21,
                    outsource_work_instruction_id=21,
                    lot_id=4,
                    process_type="CUT",
                    is_active=True,
                ),
                OutsourceWorkInstructionFile(
                    outsource_work_instruction_file_id=20,
                    outsource_work_instruction_id=20,
                    file_name="plate.pdf",
                    file_path="/tmp/plate.pdf",
                    content_type="application/pdf",
                ),
                OutsourceWorkGroup(
                    outsource_work_group_id=20,
                    outsource_work_instruction_id=20,
                    group_seq="G-020",
                    process_type="CUT",
                    is_bundle=False,
                    sheet_qty=300,
                    sheet_cut_count=1,
                    status=None,
                    representative_lot_id=3,
                ),
                OutsourceWorkGroup(
                    outsource_work_group_id=21,
                    outsource_work_instruction_id=21,
                    group_seq="G-021",
                    process_type="CUT",
                    is_bundle=False,
                    sheet_qty=400,
                    sheet_cut_count=1,
                    status=None,
                    representative_lot_id=4,
                ),
                OutsourceWorkGroupItem(
                    outsource_work_group_item_id=20,
                    outsource_work_group_id=20,
                    lot_id=3,
                    cuts_per_sheet=1,
                    expected_output_qty=300,
                ),
                OutsourceWorkGroupItem(
                    outsource_work_group_item_id=21,
                    outsource_work_group_id=21,
                    lot_id=4,
                    cuts_per_sheet=1,
                    expected_output_qty=400,
                ),
            ]
        )
        self.db.commit()

    def _seed_purchase_orders(self) -> None:
        self.db.add_all(
            [
                OutsourcePurchaseOrder(
                    outsource_purchase_order_id=1,
                    purchase_order_no="OCUT-20260103-001",
                    purchase_order_date=date(2026, 1, 3),
                    due_date=date(2026, 1, 8),
                    process_type="CUT",
                    outsource_partner_id=1,
                    inbound_partner_id=2,
                    work_description="cut work",
                    remark="normal",
                    qty=300,
                    unit_price=Decimal("10.00"),
                    supply_amount=Decimal("3000.00"),
                    vat_amount=Decimal("300.00"),
                    total_amount=Decimal("3300.00"),
                ),
                OutsourcePurchaseOrder(
                    outsource_purchase_order_id=2,
                    purchase_order_no="OPRT-20260104-001",
                    purchase_order_date=date(2026, 1, 4),
                    process_type="PRINT",
                    outsource_partner_id=1,
                    remark="urgent print",
                    qty=100,
                ),
                OutsourcePurchaseOrder(
                    outsource_purchase_order_id=3,
                    purchase_order_no="OCUT-20260104-002",
                    purchase_order_date=date(2026, 1, 4),
                    process_type="CUT",
                    outsource_partner_id=5,
                    remark="later cut",
                    qty=50,
                ),
                OutsourcePurchaseOrderItem(
                    outsource_purchase_order_item_id=1,
                    outsource_purchase_order_id=1,
                    lot_id=1,
                    outsource_work_instruction_id=10,
                    item_seq=2,
                    qty=100,
                    status=None,
                ),
                OutsourcePurchaseOrderItem(
                    outsource_purchase_order_item_id=2,
                    outsource_purchase_order_id=1,
                    lot_id=2,
                    outsource_work_instruction_id=11,
                    item_seq=1,
                    qty=200,
                    status="VENDOR_RECEIVED",
                ),
                OutsourcePurchaseOrderGroup(
                    outsource_purchase_order_group_id=21,
                    outsource_purchase_order_id=3,
                    outsource_work_group_id=21,
                    item_seq=1,
                    status=None,
                ),
            ]
        )
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
