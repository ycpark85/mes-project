from __future__ import annotations

import unittest
from datetime import date

from fastapi import HTTPException
from sqlalchemy import BigInteger, create_engine, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

import app.models  # noqa: F401
from app.db.base import Base
from app.models.drawing import Drawing
from app.models.lot import Lot
from app.models.lot_step import LotStep
from app.models.order_line import OrderLine
from app.models.partner import Partner
from app.models.process import Process
from app.models.product import Product
from app.models.routing_template import RoutingTemplate
from app.models.routing_template_step import RoutingTemplateStep
from app.schemas.lot import LotCreate
from app.services.lot_rework_service import create_rework_lot


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, compiler, **kw):
    return "INTEGER"


TEST_TABLE_NAMES = [
    "partner",
    "drawing",
    "routing_template",
    "process",
    "routing_template_step",
    "product",
    "order_line",
    "lot",
    "lot_step",
    "production_progress_snapshot",
]


class LotReworkServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        tables = [Base.metadata.tables[name] for name in TEST_TABLE_NAMES]
        Base.metadata.create_all(self.engine, tables=tables)

        SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()
        self._seed_base_data(parent_status="DONE", order_status="DONE")

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_create_rework_lot_creates_child_lot_steps_and_reopens_done_order(self) -> None:
        with patch("app.services.lot_rework_service.refresh_order_line_snapshot", return_value=None):
            result = create_rework_lot(
                self.db,
                LotCreate(
                    order_line_id=1,
                    parent_lot_id=1,
                    lot_qty=5,
                    created_date=date(2026, 7, 11),
                    memo="rework",
                ),
            )
            self.db.commit()

        order_line = self.db.get(OrderLine, 1)
        created_lot = self.db.get(Lot, result.lot_id)
        steps = (
            self.db.execute(
                select(LotStep)
                .where(LotStep.lot_id == result.lot_id)
                .order_by(LotStep.step_seq.asc())
            )
            .scalars()
            .all()
        )

        self.assertEqual("CLOSED", order_line.status)
        self.assertEqual(1, created_lot.parent_lot_id)
        self.assertEqual(5, created_lot.lot_qty)
        self.assertEqual("WAITING", created_lot.status)
        self.assertEqual("rework", created_lot.memo)
        self.assertEqual("CT26G11E01", created_lot.lot_no)
        self.assertEqual("SO-1", result.order_no)
        self.assertEqual("Customer A", result.partner_name)
        self.assertEqual("PRD-A", result.product_code)
        self.assertEqual(1, len(steps))
        self.assertEqual("CUT", steps[0].process_code)

    def test_create_rework_lot_rejects_missing_parent_lot(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            create_rework_lot(
                self.db,
                LotCreate(
                    order_line_id=1,
                    parent_lot_id=None,
                    lot_qty=5,
                    created_date=date(2026, 7, 11),
                ),
            )

        self.assertEqual(409, ctx.exception.status_code)

    def test_create_rework_lot_rejects_blank_rework_reason(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            create_rework_lot(
                self.db,
                LotCreate(
                    order_line_id=1,
                    parent_lot_id=1,
                    lot_qty=5,
                    created_date=date(2026, 7, 11),
                    memo="   ",
                ),
            )

        self.assertEqual(422, ctx.exception.status_code)
        self.assertEqual("Rework reason is required", ctx.exception.detail)

    def test_create_rework_lot_rejects_parent_not_done_or_canceled(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        tables = [Base.metadata.tables[name] for name in TEST_TABLE_NAMES]
        Base.metadata.create_all(self.engine, tables=tables)
        SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()
        self._seed_base_data(parent_status="IN_PROGRESS", order_status="CLOSED")

        with self.assertRaises(HTTPException) as ctx:
            create_rework_lot(
                self.db,
                LotCreate(
                    order_line_id=1,
                    parent_lot_id=1,
                    lot_qty=5,
                    created_date=date(2026, 7, 11),
                ),
            )

        self.assertEqual(409, ctx.exception.status_code)

    def _seed_base_data(self, *, parent_status: str, order_status: str) -> None:
        self.db.add_all(
            [
                Partner(
                    partner_id=1,
                    partner_type="CUSTOMER",
                    name="Customer A",
                    business_no="100-00-00001",
                    is_active=True,
                ),
                Drawing(drawing_id=1, drawing_no="DWG-A", is_active=True),
                RoutingTemplate(
                    routing_template_id=1,
                    template_code="RT-A",
                    template_name="Default",
                    is_active=True,
                ),
                Process(
                    process_id=1,
                    process_code="CUT",
                    process_name="Cutting",
                    process_type="OUTSOURCE",
                    is_active=True,
                ),
                RoutingTemplateStep(
                    routing_template_step_id=1,
                    routing_template_id=1,
                    step_seq=10,
                    process_id=1,
                    default_process_type="OUTSOURCE",
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
                    order_qty=10,
                    uom="EA",
                    status=order_status,
                    is_active=True,
                ),
                Lot(
                    lot_id=1,
                    lot_no="LOT-PARENT",
                    order_line_id=1,
                    product_id=1,
                    lot_qty=10,
                    uom="EA",
                    created_date=date(2026, 7, 1),
                    due_date=date(2026, 7, 20),
                    status=parent_status,
                ),
            ]
        )
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
