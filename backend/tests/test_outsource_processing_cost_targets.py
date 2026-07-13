from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.outsource_processing_cost_allocation import (
    OutsourceProcessingCostAllocation,
)
from app.models.outsource_processing_cost_group import OutsourceProcessingCostGroup
from app.models.outsource_processing_cost_work_group import (
    OutsourceProcessingCostWorkGroup,
)
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.models.partner import Partner
from app.services.outsource_processing_cost_target_query import (
    build_target_cost_fields,
    find_target_cost_group_for_work_group,
)


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, compiler, **kw):
    return "INTEGER"


TEST_TABLE_NAMES = [
    "partner",
    "outsource_work_instruction",
    "outsource_work_group",
    "outsource_processing_cost_group",
    "outsource_processing_cost_work_group",
    "outsource_processing_cost_allocation",
]


class OutsourceProcessingCostTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        tables = [Base.metadata.tables[name] for name in TEST_TABLE_NAMES]
        Base.metadata.create_all(self.engine, tables=tables)

        SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_find_target_cost_group_ignores_canceled_group_by_default(self) -> None:
        self._seed_work_group_with_cost_group(status="CANCELED")

        cost_group = find_target_cost_group_for_work_group(self.db, "CUT", 1)

        self.assertIsNone(cost_group)

    def test_find_target_cost_group_can_include_canceled_group(self) -> None:
        self._seed_work_group_with_cost_group(status="CANCELED")

        cost_group = find_target_cost_group_for_work_group(
            self.db,
            "CUT",
            1,
            include_canceled=True,
        )

        self.assertIsNotNone(cost_group)
        self.assertEqual("CANCELED", cost_group.status)

    def test_build_target_cost_fields_returns_work_group_allocated_amounts(self) -> None:
        self._seed_work_group_with_cost_group(status="DRAFT")
        self._add_allocation(
            allocation_id=1,
            work_group_id=1,
            standard_amount=Decimal("12000"),
            actual_amount=Decimal("15000"),
        )
        self._add_allocation(
            allocation_id=2,
            work_group_id=2,
            standard_amount=Decimal("8000"),
            actual_amount=Decimal("5000"),
        )

        cost_group = self.db.get(OutsourceProcessingCostGroup, 1)
        fields = build_target_cost_fields(self.db, cost_group, 1)

        self.assertEqual(Decimal("12000"), fields["standard_amount"])
        self.assertEqual(Decimal("15000"), fields["actual_amount"])
        self.assertEqual(Decimal("3000"), fields["amount_difference"])

    def _seed_work_group_with_cost_group(self, *, status: str) -> None:
        self.db.add(
            Partner(
                partner_id=1,
                partner_type="VENDOR",
                name="Vendor",
                business_no="100",
                is_active=True,
            )
        )
        self.db.add(
            OutsourceWorkInstruction(
                outsource_work_instruction_id=1,
                instruction_no="OWI260708001",
                instruction_date=date(2026, 7, 8),
                process_type="CUT",
                partner_id=1,
                is_bundle=False,
            )
        )
        self.db.add(
            OutsourceWorkGroup(
                outsource_work_group_id=1,
                outsource_work_instruction_id=1,
                group_seq="A001",
                process_type="CUT",
                is_bundle=False,
                sheet_qty=10,
                sheet_cut_count=1,
            )
        )
        self.db.add(
            OutsourceProcessingCostGroup(
                outsource_processing_cost_group_id=1,
                cost_group_no="OPC-CUT-202607-0001",
                settlement_month=date(2026, 7, 1),
                process_type="CUT",
                status=status,
                standard_amount=Decimal("1000"),
                actual_amount=Decimal("1000"),
            )
        )
        self.db.add(
            OutsourceProcessingCostWorkGroup(
                outsource_processing_cost_work_group_id=1,
                outsource_processing_cost_group_id=1,
                outsource_work_group_id=1,
            )
        )
        self.db.commit()

    def _add_allocation(
        self,
        *,
        allocation_id: int,
        work_group_id: int,
        standard_amount: Decimal,
        actual_amount: Decimal,
    ) -> None:
        self.db.add(
            OutsourceProcessingCostAllocation(
                outsource_processing_cost_allocation_id=allocation_id,
                outsource_processing_cost_group_id=1,
                outsource_work_group_id=work_group_id,
                lot_id=allocation_id,
                lot_no_snapshot=f"LOT-{allocation_id:03d}",
                product_code_snapshot=f"P-{allocation_id:03d}",
                product_name_snapshot="Product",
                basis_type="AREA",
                basis_value=Decimal("1"),
                basis_area_sqm=Decimal("1"),
                allocation_ratio=Decimal("0.5"),
                standard_allocated_amount=standard_amount,
                actual_allocated_amount=actual_amount,
            )
        )
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
