from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import BigInteger, create_engine, select
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
from app.models.product_inventory_movement import ProductInventoryMovement
from app.models.routing_template import RoutingTemplate
from app.models.shipment_line import ShipmentLine
from app.services.inspection_result_service import upsert_inspection_result


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, compiler, **kw):
    return "INTEGER"


TEST_TABLE_NAMES = [
    "drawing",
    "routing_template",
    "partner",
    "product",
    "order_line",
    "lot",
    "inspection_schedule",
    "inspection_result",
    "defect_type",
    "inspection_defect",
    "inspection_defect_attachment",
    "product_inventory",
    "product_inventory_lot",
    "product_inventory_movement",
    "shipment_line",
]


class InspectionResultServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        tables = [Base.metadata.tables[name] for name in TEST_TABLE_NAMES]
        Base.metadata.create_all(self.engine, tables=tables)

        SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()
        self._seed_base_data()

        self.snapshot_patches = [
            patch("app.services.inspection_result_service.refresh_order_line_snapshots_for_lots", return_value=0),
            patch("app.services.inspection_result_service.refresh_order_line_snapshots_for_product", return_value=0),
        ]
        for patcher in self.snapshot_patches:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in self.snapshot_patches:
            patcher.stop()
        self.db.close()
        self.engine.dispose()

    def test_partial_result_creates_next_received_schedule_without_inventory_settlement(self) -> None:
        result, schedule_status, created_next_id = upsert_inspection_result(
            self.db,
            1,
            good_qty=10,
            defect_ship_qty=2,
            defect_qty=1,
            uninspected_qty=99,
            stock_ship_qty=4,
            result_ship_qty=5,
            stock_in_qty=6,
            discard_qty=7,
            is_partial=True,
            next_inspection_date=date(2026, 7, 11),
            partial_reason="partial",
            memo="first partial",
            defects=[],
            actor="tester",
        )
        self.db.commit()

        schedule = self.db.get(InspectionSchedule, 1)
        next_schedule = self.db.get(InspectionSchedule, created_next_id)
        movements = self.db.execute(select(ProductInventoryMovement)).scalars().all()
        shipments = self.db.execute(select(ShipmentLine)).scalars().all()

        self.assertEqual("PARTIAL_DONE", schedule_status)
        self.assertEqual("PARTIAL_DONE", schedule.status)
        self.assertEqual("RECEIVED", next_schedule.status)
        self.assertEqual(date(2026, 7, 11), next_schedule.inspection_date)
        self.assertEqual(0, result.uninspected_qty)
        self.assertEqual(0, len(movements))
        self.assertEqual(0, len(shipments))

    def test_done_result_applies_inventory_in_stock_ship_and_result_ship(self) -> None:
        self._add_stock_for_done_settlement()

        result, schedule_status, created_next_id = upsert_inspection_result(
            self.db,
            1,
            good_qty=40,
            defect_ship_qty=10,
            defect_qty=4,
            uninspected_qty=1,
            stock_ship_qty=6,
            result_ship_qty=20,
            stock_in_qty=27,
            discard_qty=3,
            is_partial=False,
            next_inspection_date=None,
            partial_reason=None,
            memo="done",
            defects=[],
            actor="tester",
        )
        self.db.commit()

        inventory = self.db.get(ProductInventory, 1)
        stock_lot = self.db.get(ProductInventoryLot, 1)
        result_lot = (
            self.db.execute(
                select(ProductInventoryLot).where(
                    ProductInventoryLot.product_id == 1,
                    ProductInventoryLot.lot_no == "LOT-A",
                )
            )
            .scalars()
            .one()
        )
        movements = (
            self.db.execute(
                select(ProductInventoryMovement).order_by(ProductInventoryMovement.inventory_movement_id.asc())
            )
            .scalars()
            .all()
        )
        shipments = (
            self.db.execute(select(ShipmentLine).order_by(ShipmentLine.shipment_line_id.asc()))
            .scalars()
            .all()
        )

        self.assertEqual("DONE", schedule_status)
        self.assertIsNone(created_next_id)
        self.assertEqual(1, result.inspection_result_id)
        self.assertEqual(41, inventory.current_qty)
        self.assertEqual(6, stock_lot.current_qty)
        self.assertEqual(27, result_lot.current_qty)
        self.assertEqual(["INSPECTION_IN", "SHIP_OUT", "SHIP_OUT"], [movement.movement_type for movement in movements])
        self.assertEqual([47, -6, -20], [movement.qty for movement in movements])
        self.assertEqual(["STOCK", "INSPECTION_RESULT"], [shipment.source_type for shipment in shipments])
        self.assertEqual(["DONE", "DONE"], [shipment.status for shipment in shipments])
        self.assertEqual([6, 20], [shipment.ship_qty for shipment in shipments])

    def test_done_result_rejects_sellable_quantity_mismatch_before_creating_result(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            upsert_inspection_result(
                self.db,
                1,
                good_qty=10,
                defect_ship_qty=0,
                defect_qty=0,
                uninspected_qty=0,
                stock_ship_qty=0,
                result_ship_qty=4,
                stock_in_qty=4,
                discard_qty=1,
                is_partial=False,
                next_inspection_date=None,
                partial_reason=None,
                memo=None,
                defects=[],
                actor="tester",
            )

        result = self.db.execute(select(InspectionResult)).scalar_one_or_none()
        self.assertEqual(422, ctx.exception.status_code)
        self.assertIsNone(result)

    def _seed_base_data(self) -> None:
        self.db.add_all(
            [
                Drawing(drawing_id=1, drawing_no="DWG-A", is_active=True),
                RoutingTemplate(
                    routing_template_id=1,
                    template_code="RT-A",
                    template_name="Default",
                    is_active=True,
                ),
                Partner(
                    partner_id=1,
                    partner_type="CUSTOMER",
                    name="Customer A",
                    business_no="100-00-00003",
                    is_active=True,
                ),
                Product(
                    product_id=1,
                    product_code="PRD-A",
                    product_name="Product A",
                    uom="EA",
                    drawing_id=1,
                    routing_template_id=1,
                    is_active=True,
                ),
                OrderLine(
                    order_line_id=1,
                    order_no="SO-1",
                    line_no=1,
                    partner_id=1,
                    product_id=1,
                    order_date=date(2026, 7, 1),
                    due_date=date(2026, 7, 20),
                    order_qty=100,
                    uom="EA",
                    status="CLOSED",
                    is_active=True,
                ),
                Lot(
                    lot_id=1,
                    lot_no="LOT-A",
                    order_line_id=1,
                    product_id=1,
                    lot_qty=80,
                    uom="EA",
                    created_date=date(2026, 7, 1),
                    due_date=date(2026, 7, 20),
                    status="IN_PROGRESS",
                ),
                InspectionSchedule(
                    inspection_schedule_id=1,
                    lot_id=1,
                    inspection_date=date(2026, 7, 10),
                    status="IN_PROGRESS",
                ),
            ]
        )
        self.db.commit()

    def _add_stock_for_done_settlement(self) -> None:
        self.db.add_all(
            [
                ProductInventory(
                    product_inventory_id=1,
                    product_id=1,
                    current_qty=20,
                ),
                ProductInventoryLot(
                    product_inventory_lot_id=1,
                    product_id=1,
                    lot_no="STOCK-1",
                    current_qty=12,
                ),
                ShipmentLine(
                    shipment_line_id=1,
                    order_line_id=1,
                    product_id=1,
                    product_inventory_lot_id=1,
                    stock_lot_no="STOCK-1",
                    lot_id=None,
                    inspection_result_id=None,
                    source_type="STOCK",
                    status="WAITING",
                    ship_qty=6,
                    shipped_qty=0,
                ),
            ]
        )
        self.db.commit()
