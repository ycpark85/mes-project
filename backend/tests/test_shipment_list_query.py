from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.order_line import OrderLine
from app.models.partner import Partner
from app.models.product import Product
from app.models.shipment_line import ShipmentLine
from app.services.shipment_list_query import list_shipments_for_grid


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, compiler, **kw):
    return "INTEGER"


TEST_TABLE_NAMES = [
    "partner",
    "drawing",
    "routing_template",
    "product",
    "product_inventory",
    "product_inventory_lot",
    "product_inventory_movement",
    "order_line",
    "lot",
    "shipment_line",
]


class ShipmentListQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        tables = [Base.metadata.tables[name] for name in TEST_TABLE_NAMES]
        Base.metadata.create_all(self.engine, tables=tables)

        SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()
        self._seed_shipments_around_korea_day_boundary()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_done_filter_uses_korea_calendar_day_boundaries(self) -> None:
        items, total = list_shipments_for_grid(
            self.db,
            status="DONE",
            page=1,
            size=20,
            shipped_from=date(2026, 7, 13),
            shipped_to=date(2026, 7, 13),
        )

        self.assertEqual(2, total)
        self.assertEqual([3, 2], [item.shipment_line_id for item in items])

    def _seed_shipments_around_korea_day_boundary(self) -> None:
        self.db.add_all(
            [
                Partner(
                    partner_id=1,
                    partner_type="CUSTOMER",
                    name="Customer",
                    business_no="100-00-00001",
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
                    order_date=date(2026, 7, 1),
                    due_date=date(2026, 7, 31),
                    order_qty=100,
                    uom="EA",
                    status="DONE",
                    is_active=True,
                ),
            ]
        )

        shipped_times = (
            datetime(2026, 7, 12, 14, 59, 59, tzinfo=timezone.utc),
            datetime(2026, 7, 12, 15, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 13, 14, 59, 59, tzinfo=timezone.utc),
            datetime(2026, 7, 13, 15, 0, tzinfo=timezone.utc),
        )
        self.db.add_all(
            [
                ShipmentLine(
                    shipment_line_id=index,
                    order_line_id=1,
                    product_id=1,
                    source_type="STOCK",
                    status="DONE",
                    ship_qty=10,
                    shipped_qty=10,
                    created_at=shipped_at,
                    shipped_at=shipped_at,
                )
                for index, shipped_at in enumerate(shipped_times, start=1)
            ]
        )
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
