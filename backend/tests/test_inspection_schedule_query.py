from __future__ import annotations

import unittest
from datetime import date

from fastapi import HTTPException
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.drawing import Drawing
from app.models.inspection_result import InspectionResult
from app.models.inspection_schedule import InspectionSchedule
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.partner import Partner
from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.product_inventory_lot import ProductInventoryLot
from app.models.routing_template import RoutingTemplate
from app.models.shipment_line import ShipmentLine
from app.services.inspection_schedule_query import (
    get_inspection_schedule_detail,
    list_inspection_stock_lots,
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
    "inspection_schedule",
    "inspection_result",
    "product_inventory",
    "product_inventory_lot",
    "shipment_line",
]


class InspectionScheduleQueryTests(unittest.TestCase):
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

    def test_stock_lots_include_current_result_allocation(self) -> None:
        result = list_inspection_stock_lots(self.db, 1)

        self.assertEqual(1, len(result.items))
        self.assertEqual("LOT-STOCK", result.items[0].lot_no)
        self.assertEqual(60, result.items[0].stock_qty)
        self.assertEqual(60, result.total_stock_qty)

    def test_get_detail_returns_schedule(self) -> None:
        result = get_inspection_schedule_detail(self.db, 1)
        self.assertEqual(1, result.inspection_schedule_id)
        self.assertEqual("WAITING", result.status)

    def test_missing_schedule_returns_not_found(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            list_inspection_stock_lots(self.db, 999)
        self.assertEqual(404, ctx.exception.status_code)

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
                Drawing(drawing_id=1, drawing_no="D-001", is_active=True),
                RoutingTemplate(
                    routing_template_id=1,
                    template_code="CUT",
                    template_name="CUT",
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
                    order_date=date(2026, 1, 1),
                    due_date=date(2026, 1, 10),
                    order_qty=100,
                    uom="EA",
                    status="OPEN",
                    is_active=True,
                ),
                Lot(
                    lot_id=1,
                    lot_no="LOT-CURRENT",
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
                    lot_no="LOT-STOCK",
                    order_line_id=1,
                    product_id=1,
                    lot_qty=80,
                    uom="EA",
                    created_date=date(2025, 12, 1),
                    due_date=date(2025, 12, 10),
                    status="DONE",
                ),
                InspectionSchedule(
                    inspection_schedule_id=1,
                    lot_id=1,
                    inspection_date=date(2026, 1, 5),
                    status="WAITING",
                    day_seq=1,
                ),
                ProductInventory(
                    product_inventory_id=1,
                    product_id=1,
                    current_qty=50,
                ),
                ProductInventoryLot(
                    product_inventory_lot_id=1,
                    product_id=1,
                    lot_no="LOT-STOCK",
                    current_qty=80,
                ),
            ]
        )
        self.db.flush()
        self.db.add(
            InspectionResult(
                inspection_result_id=1,
                inspection_schedule_id=1,
                good_qty=0,
                defect_ship_qty=0,
                defect_qty=0,
                inspected_qty=0,
                uninspected_qty=0,
                discard_qty=0,
                is_partial=False,
            )
        )
        self.db.flush()
        self.db.add(
            ShipmentLine(
                shipment_line_id=1,
                order_line_id=1,
                product_id=1,
                product_inventory_lot_id=1,
                stock_lot_no="LOT-STOCK",
                lot_id=2,
                inspection_result_id=1,
                source_type="STOCK",
                status="WAITING",
                ship_qty=10,
                shipped_qty=0,
            )
        )
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
