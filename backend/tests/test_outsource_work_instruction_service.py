from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch

from sqlalchemy import BigInteger, create_engine, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.outsource_work_instruction_item import OutsourceWorkInstructionItem
from app.models.partner import Partner
from app.models.product import Product
from app.models.routing_template import RoutingTemplate
from app.schemas.outsource_work_instruction import (
    OutsourceWorkInstructionBatchCreate,
    OutsourceWorkInstructionBatchGroupCreate,
    OutsourceWorkInstructionFileCreate,
)
from app.services.outsource_work_instruction_service import create_work_instruction_batch


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
    "outsource_work_instruction_item",
    "outsource_work_instruction_file",
    "outsource_work_group",
    "outsource_work_group_item",
    "raw_material",
    "raw_material_location",
    "raw_material_inventory",
    "raw_material_inventory_lot",
    "raw_material_inventory_movement",
    "outsource_work_group_raw_material_allocation",
]


class OutsourceWorkInstructionServiceTests(unittest.TestCase):
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

    def test_create_work_instruction_batch_splits_cut_and_print_lots(self) -> None:
        payload = OutsourceWorkInstructionBatchCreate(
            instruction_date=date(2026, 1, 5),
            groups=[
                OutsourceWorkInstructionBatchGroupCreate(
                    customer_partner_id=2,
                    lot_ids=[1, 2],
                    files=[
                        OutsourceWorkInstructionFileCreate(
                            file_name="plate.pdf",
                            file_path="/tmp/plate.pdf",
                            content_type="application/pdf",
                        )
                    ],
                )
            ],
        )

        with patch(
            "app.services.outsource_work_instruction_service.refresh_order_line_snapshots_for_lots"
        ) as refresh:
            instructions = create_work_instruction_batch(self.db, payload)

        self.assertEqual(["CUT", "PRINT"], [item.process_type for item in instructions])

        rows = (
            self.db.execute(
                select(OutsourceWorkInstructionItem)
                .order_by(OutsourceWorkInstructionItem.outsource_work_instruction_item_id.asc())
            )
            .scalars()
            .all()
        )

        self.assertEqual([(1, "CUT"), (2, "PRINT")], [(row.lot_id, row.process_type) for row in rows])
        refresh.assert_called_once_with(self.db, {1, 2})

    def _seed_data(self) -> None:
        self.db.add_all(
            [
                Partner(
                    partner_id=1,
                    partner_type="CUSTOMER",
                    name="Inactive Customer",
                    business_no="C-000",
                    is_active=False,
                ),
                Partner(
                    partner_id=2,
                    partner_type="CUSTOMER",
                    name="Customer",
                    business_no="C-001",
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
                Product(
                    product_id=1,
                    product_code="P-001",
                    product_name="Blank Product",
                    uom="EA",
                    drawing_id=1,
                    routing_template_id=1,
                    cut_qty_per_panel=2,
                    is_active=True,
                ),
                Product(
                    product_id=2,
                    product_code="P-002",
                    product_name="Print Product",
                    uom="EA",
                    drawing_id=2,
                    routing_template_id=2,
                    cut_qty_per_panel=3,
                    is_active=True,
                ),
                OrderLine(
                    order_line_id=1,
                    order_no="SO-001",
                    line_no=1,
                    partner_id=2,
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
                    partner_id=2,
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
                    created_date=date(2026, 1, 3),
                    due_date=date(2026, 1, 10),
                    status="WAITING",
                ),
            ]
        )
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
