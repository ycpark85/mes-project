from __future__ import annotations

import unittest
from datetime import date

from sqlalchemy import BigInteger, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.drawing import Drawing
from app.models.inspection_schedule import InspectionSchedule
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.outsource_purchase_order import OutsourcePurchaseOrder
from app.models.outsource_purchase_order_group import OutsourcePurchaseOrderGroup
from app.models.outsource_purchase_order_item import OutsourcePurchaseOrderItem
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.models.partner import Partner
from app.models.product import Product
from app.models.routing_template import RoutingTemplate
from app.services.outsource_legacy_status_audit import (
    audit_outsource_legacy_item_status,
    has_outsource_legacy_status_risk,
)


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, compiler, **kw):
    return "INTEGER"


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(_type, compiler, **kw):
    return "JSON"


TEST_TABLE_NAMES = [
    "partner",
    "drawing",
    "routing_template",
    "product",
    "order_line",
    "lot",
    "outsource_work_instruction",
    "outsource_work_group",
    "outsource_work_group_item",
    "outsource_purchase_order",
    "outsource_purchase_order_item",
    "outsource_purchase_order_group",
    "inspection_schedule",
]


class OutsourceLegacyStatusAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        tables = [Base.metadata.tables[name] for name in TEST_TABLE_NAMES]
        Base.metadata.create_all(self.engine, tables=tables)

        SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_clean_work_group_status_has_no_legacy_risk(self) -> None:
        self._seed_base_rows()
        self._add_current_flow_rows(item_status=None, work_group_status=None)
        self.db.commit()

        report = audit_outsource_legacy_item_status(self.db)

        self.assertEqual(0, report["progressed_purchase_order_item_count"])
        self.assertEqual(0, report["item_work_group_status_mismatch_count"])
        self.assertEqual(0, report["legacy_schedule_fallback_count"])
        self.assertFalse(has_outsource_legacy_status_risk(report))

    def test_progressed_item_status_reports_legacy_risk(self) -> None:
        self._seed_base_rows()
        self._add_current_flow_rows(
            item_status="SHIPPED",
            work_group_status=None,
        )
        self.db.add(
            InspectionSchedule(
                inspection_schedule_id=1,
                lot_id=1,
                inspection_date=date(2026, 1, 5),
                status="WAITING",
            )
        )
        self.db.commit()

        report = audit_outsource_legacy_item_status(self.db)

        self.assertEqual(1, report["progressed_purchase_order_item_count"])
        self.assertEqual(1, report["item_work_group_status_mismatch_count"])
        self.assertEqual(1, report["legacy_schedule_fallback_count"])
        self.assertTrue(has_outsource_legacy_status_risk(report))
        self.assertEqual(
            1,
            report["item_work_group_status_mismatch_samples"][0][
                "purchase_order_item_id"
            ],
        )

    def test_item_without_matching_work_group_is_reported(self) -> None:
        self._seed_base_rows()
        self.db.add(
            OutsourcePurchaseOrder(
                outsource_purchase_order_id=1,
                purchase_order_no="OCUT-20260101-001",
                purchase_order_date=date(2026, 1, 1),
                process_type="CUT",
                outsource_partner_id=2,
                qty=100,
            )
        )
        self.db.add(
            OutsourcePurchaseOrderItem(
                outsource_purchase_order_item_id=1,
                outsource_purchase_order_id=1,
                lot_id=1,
                outsource_work_instruction_id=999,
                item_seq=1,
                qty=100,
                status=None,
            )
        )
        self.db.commit()

        report = audit_outsource_legacy_item_status(self.db)

        self.assertEqual(1, report["purchase_order_item_without_work_group_match_count"])
        self.assertTrue(has_outsource_legacy_status_risk(report))
        self.assertEqual(
            999,
            report["purchase_order_item_without_work_group_match_samples"][0][
                "work_instruction_id"
            ],
        )

    def _seed_base_rows(self) -> None:
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
                    template_code="PLAIN",
                    template_name="무지",
                    is_active=True,
                ),
                Drawing(
                    drawing_id=1,
                    drawing_no="D-001",
                    is_active=True,
                ),
                Product(
                    product_id=1,
                    product_code="P-001",
                    product_name="Product",
                    uom="EA",
                    drawing_id=1,
                    routing_template_id=1,
                    is_active=True,
                ),
                OrderLine(
                    order_line_id=1,
                    order_no="SO-001",
                    line_no=1,
                    partner_id=1,
                    product_id=1,
                    order_qty=100,
                    uom="EA",
                    order_date=date(2026, 1, 1),
                    due_date=date(2026, 1, 10),
                    status="OPEN",
                ),
                Lot(
                    lot_id=1,
                    lot_no="LOT-001",
                    order_line_id=1,
                    product_id=1,
                    lot_qty=100,
                    uom="EA",
                    created_date=date(2026, 1, 1),
                    due_date=date(2026, 1, 10),
                    status="WAITING",
                ),
            ]
        )

    def _add_current_flow_rows(
        self,
        *,
        item_status: str | None,
        work_group_status: str | None,
    ) -> None:
        self.db.add_all(
            [
                OutsourceWorkInstruction(
                    outsource_work_instruction_id=1,
                    instruction_no="OWI-001",
                    instruction_date=date(2026, 1, 1),
                    process_type="CUT",
                    partner_id=2,
                    is_bundle=False,
                ),
                OutsourceWorkGroup(
                    outsource_work_group_id=1,
                    outsource_work_instruction_id=1,
                    group_seq="A0101",
                    process_type="CUT",
                    is_bundle=False,
                    sheet_qty=100,
                    sheet_cut_count=1,
                    status=work_group_status,
                ),
                OutsourceWorkGroupItem(
                    outsource_work_group_item_id=1,
                    outsource_work_group_id=1,
                    lot_id=1,
                    cuts_per_sheet=1,
                    expected_output_qty=100,
                ),
                OutsourcePurchaseOrder(
                    outsource_purchase_order_id=1,
                    purchase_order_no="OCUT-20260101-001",
                    purchase_order_date=date(2026, 1, 1),
                    process_type="CUT",
                    outsource_partner_id=2,
                    qty=100,
                ),
                OutsourcePurchaseOrderItem(
                    outsource_purchase_order_item_id=1,
                    outsource_purchase_order_id=1,
                    lot_id=1,
                    outsource_work_instruction_id=1,
                    item_seq=1,
                    qty=100,
                    status=item_status,
                ),
                OutsourcePurchaseOrderGroup(
                    outsource_purchase_order_group_id=1,
                    outsource_purchase_order_id=1,
                    outsource_work_group_id=1,
                    item_seq=1,
                    status=work_group_status,
                ),
            ]
        )


if __name__ == "__main__":
    unittest.main()
