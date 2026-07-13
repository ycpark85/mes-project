from __future__ import annotations

import unittest
from datetime import date, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import BigInteger, create_engine, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.outsource_processing_cost_allocation import OutsourceProcessingCostAllocation
from app.models.outsource_processing_cost_group import OutsourceProcessingCostGroup
from app.models.outsource_processing_cost_work_group import (
    OutsourceProcessingCostWorkGroup,
)
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.models.partner import Partner
from app.models.product import Product
from app.models.routing_template import RoutingTemplate
from app.schemas.outsource_processing_cost import (
    OutsourceProcessingCostCreate,
    OutsourceProcessingCostUpdate,
)
from app.services.outsource_processing_cost_service import (
    cancel_processing_cost_group,
    close_processing_cost_group,
    create_processing_cost_group,
    reopen_processing_cost_group,
    update_processing_cost_group,
)


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
    "outsource_work_group",
    "outsource_work_group_item",
    "outsource_processing_cost_group",
    "outsource_processing_cost_work_group",
    "outsource_processing_cost_allocation",
]


class OutsourceProcessingCostServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        tables = [Base.metadata.tables[name] for name in TEST_TABLE_NAMES]
        Base.metadata.create_all(self.engine, tables=tables)

        SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_close_processing_cost_group_requires_actual_amount(self) -> None:
        self._add_cost_group(1, status="DRAFT", actual_amount=None)

        with self.assertRaises(HTTPException) as ctx:
            close_processing_cost_group(self.db, 1)

        self.assertEqual(409, ctx.exception.status_code)

    def test_close_processing_cost_group_sets_closed(self) -> None:
        self._add_cost_group(1, status="DRAFT", actual_amount=Decimal("1000"))

        cost_group = close_processing_cost_group(self.db, 1)

        self.assertEqual("CLOSED", cost_group.status)
        self.assertIsNotNone(cost_group.closed_at)

    def test_reopen_processing_cost_group_sets_draft(self) -> None:
        self._add_cost_group(
            1,
            status="CLOSED",
            actual_amount=Decimal("1000"),
            closed_at=datetime(2026, 7, 8),
        )

        cost_group = reopen_processing_cost_group(self.db, 1)

        self.assertEqual("DRAFT", cost_group.status)
        self.assertIsNone(cost_group.closed_at)

    def test_reopen_processing_cost_group_rejects_non_closed(self) -> None:
        self._add_cost_group(1, status="DRAFT", actual_amount=Decimal("1000"))

        with self.assertRaises(HTTPException) as ctx:
            reopen_processing_cost_group(self.db, 1)

        self.assertEqual(409, ctx.exception.status_code)

    def test_cancel_processing_cost_group_sets_canceled(self) -> None:
        self._add_cost_group(1, status="DRAFT", actual_amount=Decimal("1000"))

        cost_group = cancel_processing_cost_group(self.db, 1)

        self.assertEqual("CANCELED", cost_group.status)
        self.assertIsNotNone(cost_group.canceled_at)

    def test_update_processing_cost_group_recalculates_allocations(self) -> None:
        self._add_cost_group(1, status="DRAFT", actual_amount=Decimal("1000"))
        self._add_allocation(1, basis_value=Decimal("1"))
        self._add_allocation(2, basis_value=Decimal("3"))

        payload = OutsourceProcessingCostUpdate(
            standard_amount=Decimal("100"),
            actual_amount=Decimal("200"),
        )
        cost_group = update_processing_cost_group(self.db, 1, payload)

        allocations = sorted(
            cost_group.allocations,
            key=lambda allocation: allocation.outsource_processing_cost_allocation_id,
        )
        self.assertEqual(Decimal("25"), allocations[0].standard_allocated_amount)
        self.assertEqual(Decimal("75"), allocations[1].standard_allocated_amount)
        self.assertEqual(Decimal("50"), allocations[0].actual_allocated_amount)
        self.assertEqual(Decimal("150"), allocations[1].actual_allocated_amount)

    def test_create_processing_cost_group_allocates_amounts_by_area_basis(self) -> None:
        self._seed_work_group_targets()

        payload = OutsourceProcessingCostCreate(
            settlement_month=date(2026, 7, 15),
            process_type="CUT",
            target_work_group_ids=[1, 2],
            standard_amount=Decimal("400"),
            actual_amount=Decimal("800"),
        )

        cost_group = create_processing_cost_group(self.db, payload)

        self.assertEqual("OPC-CUT-202607-0001", cost_group.cost_group_no)
        self.assertEqual(date(2026, 7, 1), cost_group.settlement_month)

        work_group_links = (
            self.db.execute(
                select(OutsourceProcessingCostWorkGroup).order_by(
                    OutsourceProcessingCostWorkGroup.outsource_work_group_id.asc()
                )
            )
            .scalars()
            .all()
        )
        allocations = (
            self.db.execute(
                select(OutsourceProcessingCostAllocation).order_by(
                    OutsourceProcessingCostAllocation.lot_id.asc()
                )
            )
            .scalars()
            .all()
        )

        self.assertEqual([1, 2], [link.outsource_work_group_id for link in work_group_links])
        self.assertEqual(2, len(allocations))
        self.assertEqual(Decimal("1.000000"), allocations[0].basis_value)
        self.assertEqual(Decimal("3.000000"), allocations[1].basis_value)
        self.assertEqual(Decimal("100"), allocations[0].standard_allocated_amount)
        self.assertEqual(Decimal("300"), allocations[1].standard_allocated_amount)
        self.assertEqual(Decimal("200"), allocations[0].actual_allocated_amount)
        self.assertEqual(Decimal("600"), allocations[1].actual_allocated_amount)

    def test_create_processing_cost_group_rejects_active_duplicate_work_group(self) -> None:
        self._seed_work_group_targets()
        self._add_cost_group(9, status="DRAFT", actual_amount=Decimal("1000"))
        self._add_work_group_link(9, cost_group_id=9, work_group_id=1)

        payload = OutsourceProcessingCostCreate(
            settlement_month=date(2026, 7, 15),
            process_type="CUT",
            target_work_group_ids=[1],
            standard_amount=Decimal("400"),
            actual_amount=Decimal("800"),
        )

        with self.assertRaises(HTTPException) as ctx:
            create_processing_cost_group(self.db, payload)

        self.assertEqual(409, ctx.exception.status_code)

    def test_create_processing_cost_group_allows_canceled_duplicate_work_group(self) -> None:
        self._seed_work_group_targets()
        self._add_cost_group(9, status="CANCELED", actual_amount=Decimal("1000"))
        self._add_work_group_link(9, cost_group_id=9, work_group_id=1)

        payload = OutsourceProcessingCostCreate(
            settlement_month=date(2026, 7, 15),
            process_type="CUT",
            target_work_group_ids=[1],
            standard_amount=Decimal("400"),
            actual_amount=Decimal("800"),
        )

        cost_group = create_processing_cost_group(self.db, payload)

        self.assertEqual("DRAFT", cost_group.status)
        self.assertEqual("OPC-CUT-202607-0002", cost_group.cost_group_no)

    def _add_cost_group(
        self,
        cost_group_id: int,
        *,
        status: str,
        actual_amount: Decimal | None,
        closed_at: datetime | None = None,
    ) -> None:
        self.db.add(
            OutsourceProcessingCostGroup(
                outsource_processing_cost_group_id=cost_group_id,
                cost_group_no=f"OPC-CUT-202607-{cost_group_id:04d}",
                settlement_month=date(2026, 7, 1),
                process_type="CUT",
                status=status,
                standard_amount=Decimal("1000"),
                actual_amount=actual_amount,
                closed_at=closed_at,
            )
        )
        self.db.commit()

    def _add_allocation(
        self,
        allocation_id: int,
        *,
        basis_value: Decimal,
    ) -> None:
        self.db.add(
            OutsourceProcessingCostAllocation(
                outsource_processing_cost_allocation_id=allocation_id,
                outsource_processing_cost_group_id=1,
                lot_id=allocation_id,
                lot_no_snapshot=f"LOT-{allocation_id:03d}",
                product_code_snapshot=f"P-{allocation_id:03d}",
                product_name_snapshot="Product",
                basis_type="AREA",
                basis_value=basis_value,
                basis_area_sqm=basis_value,
                allocation_ratio=Decimal("0"),
            )
        )
        self.db.commit()

    def _add_work_group_link(
        self,
        link_id: int,
        *,
        cost_group_id: int,
        work_group_id: int,
    ) -> None:
        self.db.add(
            OutsourceProcessingCostWorkGroup(
                outsource_processing_cost_work_group_id=link_id,
                outsource_processing_cost_group_id=cost_group_id,
                outsource_work_group_id=work_group_id,
            )
        )
        self.db.commit()

    def _seed_work_group_targets(self) -> None:
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
                    template_name="Blank",
                    is_active=True,
                ),
                Product(
                    product_id=1,
                    product_code="P-001",
                    product_name="Product 1",
                    uom="EA",
                    drawing_id=1,
                    routing_template_id=1,
                    panel_width_mm=1000,
                    panel_length_mm=1000,
                    is_active=True,
                ),
                Product(
                    product_id=2,
                    product_code="P-002",
                    product_name="Product 2",
                    uom="EA",
                    drawing_id=2,
                    routing_template_id=1,
                    panel_width_mm=1000,
                    panel_length_mm=1000,
                    is_active=True,
                ),
                OrderLine(
                    order_line_id=1,
                    order_no="SO-001",
                    line_no=1,
                    partner_id=1,
                    product_id=1,
                    order_date=date(2026, 7, 1),
                    due_date=date(2026, 7, 10),
                    order_qty=10,
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
                    order_date=date(2026, 7, 1),
                    due_date=date(2026, 7, 10),
                    order_qty=10,
                    uom="EA",
                    status="OPEN",
                    is_active=True,
                ),
                Lot(
                    lot_id=1,
                    lot_no="LOT-001",
                    order_line_id=1,
                    product_id=1,
                    lot_qty=1,
                    uom="EA",
                    created_date=date(2026, 7, 1),
                    due_date=date(2026, 7, 10),
                    status="WAITING",
                ),
                Lot(
                    lot_id=2,
                    lot_no="LOT-002",
                    order_line_id=2,
                    product_id=2,
                    lot_qty=3,
                    uom="EA",
                    created_date=date(2026, 7, 1),
                    due_date=date(2026, 7, 10),
                    status="WAITING",
                ),
                OutsourceWorkInstruction(
                    outsource_work_instruction_id=1,
                    instruction_no="OWI-001",
                    instruction_date=date(2026, 7, 2),
                    process_type="CUT",
                    partner_id=2,
                    is_bundle=True,
                ),
                OutsourceWorkGroup(
                    outsource_work_group_id=1,
                    outsource_work_instruction_id=1,
                    group_seq="G-001",
                    process_type="CUT",
                    is_bundle=False,
                    sheet_qty=1,
                    sheet_cut_count=1,
                    representative_lot_id=1,
                ),
                OutsourceWorkGroup(
                    outsource_work_group_id=2,
                    outsource_work_instruction_id=1,
                    group_seq="G-002",
                    process_type="CUT",
                    is_bundle=False,
                    sheet_qty=3,
                    sheet_cut_count=1,
                    representative_lot_id=2,
                ),
                OutsourceWorkGroupItem(
                    outsource_work_group_item_id=1,
                    outsource_work_group_id=1,
                    lot_id=1,
                    cuts_per_sheet=1,
                    expected_output_qty=1,
                ),
                OutsourceWorkGroupItem(
                    outsource_work_group_item_id=2,
                    outsource_work_group_id=2,
                    lot_id=2,
                    cuts_per_sheet=1,
                    expected_output_qty=3,
                ),
            ]
        )
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
