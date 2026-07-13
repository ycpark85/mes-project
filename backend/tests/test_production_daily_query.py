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
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.outsource_purchase_order import OutsourcePurchaseOrder
from app.models.outsource_purchase_order_item import OutsourcePurchaseOrderItem
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.models.outsource_work_instruction_item import OutsourceWorkInstructionItem
from app.models.partner import Partner
from app.models.product import Product
from app.models.routing_template import RoutingTemplate
from app.services.production_daily_query import (
    _get_lot_progress,
    _load_work_statuses_by_lot,
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
    "outsource_work_instruction_item",
    "outsource_work_group",
    "outsource_work_group_item",
    "outsource_purchase_order",
    "outsource_purchase_order_item",
]


class ProductionDailyQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        tables = [Base.metadata.tables[name] for name in TEST_TABLE_NAMES]
        Base.metadata.create_all(self.engine, tables=tables)

        SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()
        self._seed_base_rows()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_work_group_status_wins_over_null_purchase_order_item_status(self) -> None:
        self._add_work_instruction()
        self._add_work_group(status="SHIPPED")
        self._add_purchase_order_item(status=None)
        self.db.commit()

        statuses_by_lot = _load_work_statuses_by_lot(self.db, [1])
        progress = _get_lot_progress(
            1,
            work_statuses_by_lot=statuses_by_lot,
            schedule_statuses_by_lot={},
            completed_lot_ids=set(),
        )

        self.assertEqual(["SHIPPED"], statuses_by_lot[1])
        self.assertEqual("OUTSOURCE_DONE", progress.process_code)

    def test_purchase_order_item_status_is_legacy_fallback_without_work_group(self) -> None:
        self._add_purchase_order_item(status="SHIPPED", instruction_id=99)
        self.db.commit()

        statuses_by_lot = _load_work_statuses_by_lot(self.db, [1])
        progress = _get_lot_progress(
            1,
            work_statuses_by_lot=statuses_by_lot,
            schedule_statuses_by_lot={},
            completed_lot_ids=set(),
        )

        self.assertEqual(["SHIPPED"], statuses_by_lot[1])
        self.assertEqual("OUTSOURCE_DONE", progress.process_code)

    def test_inspection_status_wins_over_work_group_status(self) -> None:
        progress = _get_lot_progress(
            1,
            work_statuses_by_lot={1: ["SHIPPED"]},
            schedule_statuses_by_lot={1: ["RECEIVED"]},
            completed_lot_ids=set(),
        )

        self.assertEqual("INSPECTION_WAITING", progress.process_code)

    def test_completed_result_wins_over_inspection_and_work_status(self) -> None:
        progress = _get_lot_progress(
            1,
            work_statuses_by_lot={1: [None]},
            schedule_statuses_by_lot={1: ["IN_PROGRESS"]},
            completed_lot_ids={1},
        )

        self.assertEqual("COMPLETED", progress.process_code)

    def test_instruction_without_group_or_purchase_order_is_outsource_ordered(self) -> None:
        self._add_work_instruction()
        self.db.commit()

        statuses_by_lot = _load_work_statuses_by_lot(self.db, [1])
        progress = _get_lot_progress(
            1,
            work_statuses_by_lot=statuses_by_lot,
            schedule_statuses_by_lot={},
            completed_lot_ids=set(),
        )

        self.assertEqual([None], statuses_by_lot[1])
        self.assertEqual("OUTSOURCE_ORDERED", progress.process_code)

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
                Drawing(
                    drawing_id=1,
                    drawing_no="D-001",
                    is_active=True,
                ),
                RoutingTemplate(
                    routing_template_id=1,
                    template_code="PLAIN",
                    template_name="plain",
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

    def _add_work_instruction(self) -> None:
        self.db.add_all(
            [
                OutsourceWorkInstruction(
                    outsource_work_instruction_id=1,
                    instruction_no="OWI-001",
                    instruction_date=date(2026, 1, 2),
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
            ]
        )

    def _add_work_group(self, *, status: str | None) -> None:
        self.db.add_all(
            [
                OutsourceWorkGroup(
                    outsource_work_group_id=1,
                    outsource_work_instruction_id=1,
                    group_seq="A0201",
                    process_type="CUT",
                    is_bundle=False,
                    sheet_qty=100,
                    sheet_cut_count=1,
                    status=status,
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

    def _add_purchase_order_item(
        self,
        *,
        status: str | None,
        instruction_id: int | None = 1,
    ) -> None:
        self.db.add_all(
            [
                OutsourcePurchaseOrder(
                    outsource_purchase_order_id=1,
                    purchase_order_no="OCUT-20260102-001",
                    purchase_order_date=date(2026, 1, 2),
                    process_type="CUT",
                    outsource_partner_id=2,
                    qty=100,
                ),
                OutsourcePurchaseOrderItem(
                    outsource_purchase_order_item_id=1,
                    outsource_purchase_order_id=1,
                    lot_id=1,
                    outsource_work_instruction_id=instruction_id,
                    item_seq=1,
                    qty=100,
                    status=status,
                ),
            ]
        )


if __name__ == "__main__":
    unittest.main()
