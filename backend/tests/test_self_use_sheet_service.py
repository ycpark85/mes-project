from __future__ import annotations

import unittest
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import BigInteger, create_engine, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.partner import Partner
from app.models.raw_material import RawMaterial
from app.models.raw_material_inventory import RawMaterialInventory
from app.models.raw_material_inventory_lot import RawMaterialInventoryLot
from app.models.raw_material_location import RawMaterialLocation
from app.models.self_use_sheet_inventory_lot import SelfUseSheetInventoryLot
from app.schemas.self_use_sheet import (
    SelfUseSheetAllocationComplete,
    SelfUseSheetAllocationCreate,
    SelfUseSheetJobCancel,
    SelfUseSheetJobComplete,
    SelfUseSheetJobCreate,
    SelfUseSheetJobStart,
    SelfUseSheetUseIn,
    SelfUseSheetUseReverseIn,
    SelfUseSheetTransferIn,
)
from app.services.self_use_sheet_service import (
    calculate_self_use_sheet_output_qty,
    cancel_self_use_sheet_job,
    complete_self_use_sheet_job,
    create_self_use_sheet_job,
    list_self_use_sheet_movements,
    reverse_self_use_sheet_usage,
    start_self_use_sheet_job,
    transfer_self_use_sheet_inventory,
    use_self_use_sheet_inventory,
)


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, compiler, **kw):
    return "INTEGER"


TEST_TABLE_NAMES = [
    "partner",
    "raw_material",
    "raw_material_location",
    "raw_material_inventory",
    "raw_material_inventory_lot",
    "raw_material_inventory_movement",
    "self_use_sheet_job",
    "self_use_sheet_raw_material_allocation",
    "self_use_sheet_inventory_lot",
    "self_use_sheet_inventory_balance",
    "self_use_sheet_inventory_movement",
]


class SelfUseSheetServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(
            self.engine,
            tables=[Base.metadata.tables[name] for name in TEST_TABLE_NAMES],
        )
        SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()
        self._seed()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_internal_cutting_consumes_raw_material_and_creates_sheet_inventory(self) -> None:
        job = create_self_use_sheet_job(
            self.db,
            SelfUseSheetJobCreate(
                purpose_type="PRINT_SETUP",
                execution_type="INTERNAL",
                cut_width_mm=Decimal("300"),
                cut_length_mm=Decimal("400"),
                planned_output_qty=50,
                expected_processing_fee=Decimal("50"),
                memo="인쇄 초기 셋팅용",
                allocations=[
                    SelfUseSheetAllocationCreate(
                        raw_material_inventory_lot_id=1,
                        planned_qty=Decimal("10"),
                    )
                ],
            ),
            actor="tester",
        )
        self.assertEqual("DRAFT", job.status)

        started = start_self_use_sheet_job(
            self.db,
            job.self_use_sheet_job_id,
            SelfUseSheetJobStart(expected_version=job.version),
            actor="tester",
        )
        self.assertEqual("IN_PROGRESS", started.status)
        self.assertEqual(Decimal("90.00"), self.db.get(RawMaterialInventoryLot, 1).current_qty)

        allocation_id = started.allocations[0].self_use_sheet_raw_material_allocation_id
        completed = complete_self_use_sheet_job(
            self.db,
            job.self_use_sheet_job_id,
            SelfUseSheetJobComplete(
                expected_version=started.version,
                produced_qty=100,
                scrap_qty=5,
                actual_processing_fee=Decimal("60"),
                allocations=[
                    SelfUseSheetAllocationComplete(
                        allocation_id=allocation_id,
                        actual_consumed_qty=Decimal("8"),
                        returned_qty=Decimal("2"),
                    )
                ],
            ),
            actor="tester",
        )
        self.assertEqual("COMPLETED", completed.status)
        self.assertEqual(Decimal("92.00"), self.db.get(RawMaterialInventoryLot, 1).current_qty)
        sheet_lot = self.db.get(SelfUseSheetInventoryLot, completed.sheet_lot_id)
        self.assertEqual(100, sheet_lot.current_qty)
        self.assertEqual(Decimal("40.00"), sheet_lot.material_amount)
        self.assertEqual(Decimal("100.00"), sheet_lot.total_cost)
        self.assertEqual(Decimal("1.0000"), sheet_lot.unit_cost)

        used = use_self_use_sheet_inventory(
            self.db,
            sheet_lot.self_use_sheet_inventory_lot_id,
            SelfUseSheetUseIn(
                expected_version=sheet_lot.version,
                purpose_type="SAMPLE",
                qty=10,
                memo="샘플 제작",
            ),
            actor="tester",
        )
        self.assertEqual(90, used.current_qty)
        movements = list_self_use_sheet_movements(
            self.db,
            sheet_lot.self_use_sheet_inventory_lot_id,
            page=1,
            size=100,
        )
        usage = next(item for item in movements.items if item.movement_type == "USE_OUT")
        restored = reverse_self_use_sheet_usage(
            self.db,
            usage.self_use_sheet_inventory_movement_id,
            SelfUseSheetUseReverseIn(expected_version=used.version, reason="수량 입력 오류"),
            actor="tester",
        )
        self.assertEqual(100, restored.current_qty)

        transferred = transfer_self_use_sheet_inventory(
            self.db,
            sheet_lot.self_use_sheet_inventory_lot_id,
            SelfUseSheetTransferIn(
                expected_version=restored.version,
                from_location_id=1,
                to_location_id=2,
                qty=20,
                reason="샘플 작업장 이동",
            ),
            actor="tester",
        )
        self.assertEqual(100, transferred.current_qty)
        self.assertEqual({1: 80, 2: 20}, {item.raw_material_location_id: item.current_qty for item in transferred.locations})

        canceled = cancel_self_use_sheet_job(
            self.db,
            job.self_use_sheet_job_id,
            SelfUseSheetJobCancel(expected_version=completed.version, reason="작업 등록 오류"),
            actor="tester",
        )
        self.assertEqual("CANCELED", canceled.status)
        self.assertEqual(Decimal("100.00"), self.db.get(RawMaterialInventoryLot, 1).current_qty)
        self.assertEqual("CANCELED", self.db.get(SelfUseSheetInventoryLot, sheet_lot.self_use_sheet_inventory_lot_id).status)

    def test_outsource_cutting_moves_stock_to_vendor_and_blocks_cancel_after_use(self) -> None:
        self.db.delete(self.db.get(RawMaterialLocation, 2))
        self.db.commit()

        job = create_self_use_sheet_job(
            self.db,
            SelfUseSheetJobCreate(
                purpose_type="SAMPLE",
                execution_type="OUTSOURCE",
                partner_id=1,
                cut_width_mm=Decimal("200"),
                cut_length_mm=Decimal("300"),
                planned_output_qty=65,
                expected_processing_fee=Decimal("100"),
                memo="샘플용",
                allocations=[
                    SelfUseSheetAllocationCreate(
                        raw_material_inventory_lot_id=1,
                        planned_qty=Decimal("20"),
                    )
                ],
            ),
            actor="tester",
        )
        started = start_self_use_sheet_job(
            self.db,
            job.self_use_sheet_job_id,
            SelfUseSheetJobStart(expected_version=job.version),
            actor="tester",
        )
        vendor_location = self.db.scalar(
            select(RawMaterialLocation).where(
                RawMaterialLocation.location_type == "OUTSOURCE_VENDOR",
                RawMaterialLocation.partner_id == 1,
                RawMaterialLocation.is_active.is_(True),
            )
        )
        self.assertIsNotNone(vendor_location)
        self.assertEqual("재단 외주처 외주 원자재", vendor_location.location_name)
        vendor_lot = self.db.scalar(
            select(RawMaterialInventoryLot).where(
                RawMaterialInventoryLot.raw_material_location_id
                == vendor_location.raw_material_location_id
            )
        )
        self.assertEqual(Decimal("80.00"), self.db.get(RawMaterialInventoryLot, 1).current_qty)
        self.assertEqual(Decimal("20.00"), vendor_lot.current_qty)

        completed = complete_self_use_sheet_job(
            self.db,
            job.self_use_sheet_job_id,
            SelfUseSheetJobComplete(
                expected_version=started.version,
                produced_qty=200,
                actual_processing_fee=Decimal("100"),
                allocations=[
                    SelfUseSheetAllocationComplete(
                        allocation_id=started.allocations[0].self_use_sheet_raw_material_allocation_id,
                        actual_consumed_qty=Decimal("18"),
                        returned_qty=Decimal("2"),
                    )
                ],
            ),
            actor="tester",
        )
        self.assertEqual(Decimal("82.00"), self.db.get(RawMaterialInventoryLot, 1).current_qty)
        self.assertEqual(Decimal("0.00"), vendor_lot.current_qty)
        sheet_lot = self.db.get(SelfUseSheetInventoryLot, completed.sheet_lot_id)
        used = use_self_use_sheet_inventory(
            self.db,
            sheet_lot.self_use_sheet_inventory_lot_id,
            SelfUseSheetUseIn(
                expected_version=sheet_lot.version,
                purpose_type="SAMPLE",
                qty=1,
                memo="샘플 제작",
            ),
            actor="tester",
        )
        with self.assertRaises(HTTPException) as context:
            cancel_self_use_sheet_job(
                self.db,
                job.self_use_sheet_job_id,
                SelfUseSheetJobCancel(expected_version=completed.version, reason="취소 시도"),
                actor="tester",
            )
        self.assertEqual(409, context.exception.status_code)
        self.assertEqual(199, used.current_qty)

    def test_stale_version_is_rejected(self) -> None:
        job = create_self_use_sheet_job(
            self.db,
            SelfUseSheetJobCreate(
                purpose_type="TEST_RND",
                execution_type="INTERNAL",
                cut_width_mm=Decimal("100"),
                cut_length_mm=Decimal("100"),
                planned_output_qty=10,
                allocations=[
                    SelfUseSheetAllocationCreate(
                        raw_material_inventory_lot_id=1,
                        planned_qty=Decimal("1"),
                    )
                ],
            ),
            actor="tester",
        )
        with self.assertRaises(HTTPException) as context:
            start_self_use_sheet_job(
                self.db,
                job.self_use_sheet_job_id,
                SelfUseSheetJobStart(expected_version=999),
                actor="tester",
            )
        self.assertEqual(409, context.exception.status_code)

    def test_expected_output_uses_existing_cutting_formula(self) -> None:
        self.assertEqual(
            50,
            calculate_self_use_sheet_output_qty(
                input_length_m=Decimal("10"),
                cut_width_mm=Decimal("300"),
                cut_length_mm=Decimal("400"),
            ),
        )
        self.assertEqual(
            65,
            calculate_self_use_sheet_output_qty(
                input_length_m=Decimal("20"),
                cut_width_mm=Decimal("200"),
                cut_length_mm=Decimal("300"),
            ),
        )

    def test_create_rejects_expected_output_that_does_not_match_formula(self) -> None:
        with self.assertRaises(HTTPException) as context:
            create_self_use_sheet_job(
                self.db,
                SelfUseSheetJobCreate(
                    purpose_type="PRINT_SETUP",
                    execution_type="INTERNAL",
                    cut_width_mm=Decimal("300"),
                    cut_length_mm=Decimal("400"),
                    planned_output_qty=51,
                    allocations=[
                        SelfUseSheetAllocationCreate(
                            raw_material_inventory_lot_id=1,
                            planned_qty=Decimal("10"),
                        )
                    ],
                ),
                actor="tester",
            )

        self.assertEqual(422, context.exception.status_code)
        self.assertEqual("Expected output quantity must be 50", context.exception.detail)

    def _seed(self) -> None:
        self.db.add_all(
            [
                Partner(
                    partner_id=1,
                    partner_type="VENDOR",
                    name="재단 외주처",
                    business_no="V-001",
                    is_active=True,
                ),
                RawMaterial(
                    raw_material_id=1,
                    material_code="RM-001",
                    material_name="테스트 원단",
                    uom="M",
                    standard_unit_cost=Decimal("5"),
                    is_active=True,
                ),
                RawMaterialLocation(
                    raw_material_location_id=1,
                    location_code="WH-001",
                    location_name="원자재 창고",
                    location_type="INTERNAL_WAREHOUSE",
                    is_active=True,
                ),
                RawMaterialLocation(
                    raw_material_location_id=2,
                    location_code="VEN-001",
                    location_name="재단 외주처",
                    location_type="OUTSOURCE_VENDOR",
                    partner_id=1,
                    is_active=True,
                ),
                RawMaterialInventory(
                    raw_material_inventory_id=1,
                    raw_material_id=1,
                    raw_material_location_id=1,
                    current_qty=Decimal("100"),
                ),
                RawMaterialInventoryLot(
                    raw_material_inventory_lot_id=1,
                    raw_material_id=1,
                    raw_material_location_id=1,
                    lot_no="RMLOT-001",
                    current_qty=Decimal("100"),
                    unit_cost=Decimal("5"),
                ),
            ]
        )
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
