from __future__ import annotations

import unittest
from datetime import date

from fastapi import HTTPException
from sqlalchemy import BigInteger, create_engine, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.api.v1 import outsource_work_instructions as api
from app.db.base import Base
from app.services import outsource_purchase_order_service as purchase_order_service
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.outsource_purchase_order import OutsourcePurchaseOrder
from app.models.outsource_purchase_order_group import OutsourcePurchaseOrderGroup
from app.models.outsource_purchase_order_item import OutsourcePurchaseOrderItem
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.models.outsource_work_instruction_item import OutsourceWorkInstructionItem
from app.models.partner import Partner
from app.models.product import Product
from app.models.routing_template import RoutingTemplate
from app.schemas.outsource_work_instruction import (
    OutsourcePurchaseOrderCreate,
    OutsourcePurchaseOrderCreateItem,
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
    "order_line",
    "lot",
    "outsource_work_instruction",
    "outsource_work_instruction_item",
    "outsource_work_group",
    "outsource_work_group_item",
    "outsource_purchase_order",
    "outsource_purchase_order_item",
    "outsource_purchase_order_group",
]


class OutsourcePurchaseOrderCreateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        tables = [Base.metadata.tables[name] for name in TEST_TABLE_NAMES]
        Base.metadata.create_all(self.engine, tables=tables)

        SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()
        self._seed_base_data()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_create_purchase_order_creates_items_and_work_group_links(self) -> None:
        payload = self._build_payload(
            [
                OutsourcePurchaseOrderCreateItem(
                    lot_id=1,
                    outsource_work_instruction_id=1,
                    item_seq=1,
                    qty=100,
                ),
                OutsourcePurchaseOrderCreateItem(
                    lot_id=2,
                    outsource_work_instruction_id=1,
                    item_seq=2,
                    qty=200,
                ),
            ]
        )

        result = api.create_outsource_purchase_order(payload, self.db)

        self.assertEqual("OCUT-20260103-001", result.purchase_order_no)
        self.assertEqual(2, len(result.items))
        self.assertEqual([1, 2], [item.lot_id for item in result.items])

        purchase_order_count = self.db.execute(
            select(OutsourcePurchaseOrder)
        ).scalars().all()
        purchase_order_items = self.db.execute(
            select(OutsourcePurchaseOrderItem)
            .order_by(OutsourcePurchaseOrderItem.item_seq.asc())
        ).scalars().all()
        purchase_order_groups = self.db.execute(
            select(OutsourcePurchaseOrderGroup)
        ).scalars().all()

        self.assertEqual(1, len(purchase_order_count))
        self.assertEqual([1, 2], [item.lot_id for item in purchase_order_items])
        self.assertEqual([1], [group.outsource_work_group_id for group in purchase_order_groups])

    def test_create_purchase_order_rejects_duplicate_lot_items(self) -> None:
        payload = self._build_payload(
            [
                OutsourcePurchaseOrderCreateItem(
                    lot_id=1,
                    outsource_work_instruction_id=1,
                    item_seq=1,
                    qty=100,
                ),
                OutsourcePurchaseOrderCreateItem(
                    lot_id=1,
                    outsource_work_instruction_id=1,
                    item_seq=2,
                    qty=100,
                ),
            ]
        )

        with self.assertRaises(HTTPException) as error:
            api.create_outsource_purchase_order(payload, self.db)

        self.assertEqual(409, error.exception.status_code)
        self.assertIn("Duplicate lot", error.exception.detail)

    def test_create_purchase_order_requires_all_lots_in_work_group(self) -> None:
        payload = self._build_payload(
            [
                OutsourcePurchaseOrderCreateItem(
                    lot_id=1,
                    outsource_work_instruction_id=1,
                    item_seq=1,
                    qty=100,
                ),
            ]
        )

        with self.assertRaises(HTTPException) as error:
            api.create_outsource_purchase_order(payload, self.db)

        self.assertEqual(409, error.exception.status_code)
        self.assertIn("All LOTs", error.exception.detail)

    def _build_payload(
        self,
        items: list[OutsourcePurchaseOrderCreateItem],
    ) -> OutsourcePurchaseOrderCreate:
        return OutsourcePurchaseOrderCreate(
            purchase_order_date=date(2026, 1, 3),
            due_date=date(2026, 1, 8),
            process_type="CUT",
            outsource_partner_id=1,
            inbound_partner_id=2,
            work_description="cut work",
            remark="normal",
            qty=sum(item.qty for item in items),
            items=items,
        )

    def _seed_base_data(self) -> None:
        outsource_partner_name = purchase_order_service._get_outsource_partner_name_by_process_type("CUT")

        self.db.add_all(
            [
                Partner(
                    partner_id=1,
                    partner_type="VENDOR",
                    name=outsource_partner_name,
                    business_no="V-001",
                    is_active=True,
                ),
                Partner(
                    partner_id=2,
                    partner_type="VENDOR",
                    name="Inbound Vendor",
                    business_no="V-002",
                    is_active=True,
                ),
                Partner(
                    partner_id=3,
                    partner_type="CUSTOMER",
                    name="Customer",
                    business_no="C-001",
                    is_active=True,
                ),
                RoutingTemplate(
                    routing_template_id=1,
                    template_code="CUT",
                    template_name="CUT",
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
                OutsourceWorkInstruction(
                    outsource_work_instruction_id=1,
                    instruction_no="OWI-001",
                    instruction_date=date(2026, 1, 3),
                    process_type="CUT",
                    partner_id=1,
                    is_bundle=True,
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
                OutsourceWorkGroup(
                    outsource_work_group_id=1,
                    outsource_work_instruction_id=1,
                    group_seq="G-001",
                    process_type="CUT",
                    is_bundle=True,
                    sheet_qty=300,
                    sheet_cut_count=2,
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
                OutsourceWorkGroupItem(
                    outsource_work_group_item_id=2,
                    outsource_work_group_id=1,
                    lot_id=2,
                    cuts_per_sheet=1,
                    expected_output_qty=200,
                ),
            ]
        )
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
