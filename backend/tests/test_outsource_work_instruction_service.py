from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import BigInteger, create_engine, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.outsource_work_instruction_item import OutsourceWorkInstructionItem
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_raw_material_allocation import OutsourceWorkGroupRawMaterialAllocation
from app.models.outsource_work_group_self_use_sheet_allocation import OutsourceWorkGroupSelfUseSheetAllocation
from app.models.outsource_work_group_self_use_sheet_source_snapshot import OutsourceWorkGroupSelfUseSheetSourceSnapshot
from app.models.partner import Partner
from app.models.product import Product
from app.models.raw_material import RawMaterial
from app.models.raw_material_inventory_movement import RawMaterialInventoryMovement
from app.models.raw_material_location import RawMaterialLocation
from app.models.routing_template import RoutingTemplate
from app.models.self_use_sheet_inventory_balance import SelfUseSheetInventoryBalance
from app.models.self_use_sheet_inventory_lot import SelfUseSheetInventoryLot
from app.models.self_use_sheet_job import SelfUseSheetJob
from app.models.self_use_sheet_raw_material_allocation import SelfUseSheetRawMaterialAllocation
from app.schemas.outsource_work_instruction import (
    OutsourceWorkInstructionBatchCreate,
    OutsourceWorkInstructionBatchGroupCreate,
    OutsourceWorkInstructionFileCreate,
    OutsourceWorkInstructionGroupCreate,
    OutsourceWorkInstructionGroupItemCreate,
    OutsourceWorkInstructionSelfUseSheetAllocationCreate,
)
from app.services.outsource_work_instruction_service import create_work_instruction_batch
from app.services.outsource_work_group_service import reverse_self_use_sheet_allocations
from app.services.raw_material_query import list_raw_material_movements_for_grid
from app.services.self_use_sheet_service import list_self_use_sheet_movements


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
    "self_use_sheet_job",
    "self_use_sheet_raw_material_allocation",
    "self_use_sheet_inventory_lot",
    "self_use_sheet_inventory_balance",
    "self_use_sheet_inventory_movement",
    "outsource_work_group_self_use_sheet_allocation",
    "outsource_work_group_self_use_sheet_source_snapshot",
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

    def test_blank_self_use_sheet_skips_cut_and_preserves_source_lot_snapshot(self) -> None:
        payload = OutsourceWorkInstructionBatchCreate(
            instruction_date=date(2026, 1, 6),
            groups=[
                OutsourceWorkInstructionBatchGroupCreate(
                    customer_partner_id=2,
                    lot_ids=[1],
                    groups=[
                        OutsourceWorkInstructionGroupCreate(
                            is_bundle=False,
                            sheet_qty=5,
                            sheet_cut_count=2,
                            representative_lot_id=1,
                            input_source_type="SELF_USE_SHEET",
                            items=[OutsourceWorkInstructionGroupItemCreate(lot_id=1, cuts_per_sheet=2)],
                            self_use_sheet_allocations=[
                                OutsourceWorkInstructionSelfUseSheetAllocationCreate(
                                    self_use_sheet_inventory_lot_id=1,
                                    source_location_id=1,
                                    qty=5,
                                )
                            ],
                        )
                    ],
                )
            ],
        )

        with patch("app.services.outsource_work_instruction_service.refresh_order_line_snapshots_for_lots"):
            instructions = create_work_instruction_batch(self.db, payload)

        self.assertEqual("DIECUT", instructions[0].process_type)
        group = self.db.scalar(select(OutsourceWorkGroup))
        self.assertEqual("SELF_USE_SHEET", group.input_source_type)
        self.assertEqual("SELF_USE_SHEET", group.cut_skipped_reason)
        self.assertEqual(15, self.db.get(SelfUseSheetInventoryLot, 1).current_qty)
        self.assertEqual(15, self.db.scalar(select(SelfUseSheetInventoryBalance.current_qty)))
        allocation = self.db.scalar(select(OutsourceWorkGroupSelfUseSheetAllocation))
        self.assertEqual("SHEET-001", allocation.sheet_lot_no)
        snapshot = self.db.scalar(select(OutsourceWorkGroupSelfUseSheetSourceSnapshot))
        self.assertEqual("RAW-LOT-001", snapshot.raw_material_lot_no_snapshot)
        movements = list_self_use_sheet_movements(self.db, page=1, size=100)
        work_use = next(item for item in movements.items if item.movement_type == "WORK_USE_OUT")
        self.assertEqual("Blank Product", work_use.usage_product_display)
        self.assertEqual("LOT-001", work_use.usage_lot_display)
        self.assertEqual("Customer", work_use.usage_partner_display)
        self.assertEqual(instructions[0].instruction_no, work_use.work_instruction_no)

        raw_allocation = OutsourceWorkGroupRawMaterialAllocation(
            outsource_work_group_id=group.outsource_work_group_id,
            raw_material_id=1,
            raw_material_location_id=1,
            lot_no="RAW-LOT-001",
            qty=Decimal("10"),
            status="CONSUMED",
        )
        self.db.add(raw_allocation)
        self.db.flush()
        self.db.add(
            RawMaterialInventoryMovement(
                raw_material_id=1,
                raw_material_location_id=1,
                lot_no="RAW-LOT-001",
                movement_type="CONSUME_OUT",
                qty=Decimal("-10"),
                balance_after=Decimal("0"),
                source_type="OUTSOURCE_WORK_GROUP_RAW_MATERIAL_ALLOCATION",
                source_id=raw_allocation.outsource_work_group_raw_material_allocation_id,
            )
        )
        self.db.flush()
        raw_movements = list_raw_material_movements_for_grid(self.db, page=1, size=100)
        raw_use = next(item for item in raw_movements.items if item.movement_type == "CONSUME_OUT")
        self.assertEqual("Blank Product", raw_use.usage_product_display)
        self.assertEqual("LOT-001", raw_use.usage_lot_display)
        self.assertEqual("Customer", raw_use.usage_partner_display)
        reverse_self_use_sheet_allocations(self.db, group, "작업지시 취소")
        self.assertEqual(20, self.db.get(SelfUseSheetInventoryLot, 1).current_qty)
        self.assertEqual("REVERSED", allocation.status)

    def test_self_use_sheet_rejects_panel_that_does_not_fit(self) -> None:
        sheet_lot = self.db.get(SelfUseSheetInventoryLot, 1)
        sheet_lot.cut_width_mm = Decimal("250")
        sheet_lot.cut_length_mm = Decimal("300")
        self.db.commit()

        payload = OutsourceWorkInstructionBatchCreate(
            instruction_date=date(2026, 1, 6),
            groups=[
                OutsourceWorkInstructionBatchGroupCreate(
                    customer_partner_id=2,
                    lot_ids=[1],
                    groups=[
                        OutsourceWorkInstructionGroupCreate(
                            is_bundle=False,
                            sheet_qty=5,
                            sheet_cut_count=2,
                            representative_lot_id=1,
                            input_source_type="SELF_USE_SHEET",
                            items=[OutsourceWorkInstructionGroupItemCreate(lot_id=1, cuts_per_sheet=2)],
                            self_use_sheet_allocations=[
                                OutsourceWorkInstructionSelfUseSheetAllocationCreate(
                                    self_use_sheet_inventory_lot_id=1,
                                    source_location_id=1,
                                    qty=5,
                                )
                            ],
                        )
                    ],
                )
            ],
        )

        with patch("app.services.outsource_work_instruction_service.refresh_order_line_snapshots_for_lots"):
            with self.assertRaisesRegex(HTTPException, "cannot contain"):
                create_work_instruction_batch(self.db, payload)

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
                    panel_width_mm=300,
                    panel_length_mm=400,
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
                    panel_width_mm=300,
                    panel_length_mm=400,
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
                RawMaterial(
                    raw_material_id=1,
                    material_code="RM-001",
                    material_name="Sample Roll",
                    uom="M",
                    is_active=True,
                ),
                RawMaterialLocation(
                    raw_material_location_id=1,
                    location_code="LOC-001",
                    location_name="Main Warehouse",
                    location_type="INTERNAL_WAREHOUSE",
                    is_active=True,
                ),
                SelfUseSheetJob(
                    self_use_sheet_job_id=1,
                    use_no="SUSE-001",
                    purpose_type="SAMPLE",
                    execution_type="INTERNAL",
                    status="COMPLETED",
                    cut_width_mm=Decimal("600"),
                    cut_length_mm=Decimal("300"),
                    planned_output_qty=20,
                    expected_processing_fee=Decimal("0"),
                    actual_processing_fee=Decimal("0"),
                    actual_input_qty=Decimal("10"),
                    produced_qty=20,
                    created_by="tester",
                    completed_by="tester",
                    completed_at=date(2026, 1, 5),
                ),
                SelfUseSheetRawMaterialAllocation(
                    self_use_sheet_raw_material_allocation_id=1,
                    self_use_sheet_job_id=1,
                    raw_material_id=1,
                    source_location_id=1,
                    lot_no="RAW-LOT-001",
                    planned_qty=Decimal("10"),
                    actual_consumed_qty=Decimal("10"),
                    returned_qty=Decimal("0"),
                    unit_cost_snapshot=Decimal("5"),
                    amount_snapshot=Decimal("50"),
                    status="CONSUMED",
                ),
                SelfUseSheetInventoryLot(
                    self_use_sheet_inventory_lot_id=1,
                    self_use_sheet_job_id=1,
                    raw_material_id=1,
                    sheet_lot_no="SHEET-001",
                    source_lot_summary="RAW-LOT-001",
                    cut_width_mm=Decimal("600"),
                    cut_length_mm=Decimal("300"),
                    initial_qty=20,
                    current_qty=20,
                    material_amount=Decimal("50"),
                    processing_fee=Decimal("0"),
                    total_cost=Decimal("50"),
                    unit_cost=Decimal("2.5"),
                    status="AVAILABLE",
                    completed_at=date(2026, 1, 5),
                ),
                SelfUseSheetInventoryBalance(
                    self_use_sheet_inventory_balance_id=1,
                    self_use_sheet_inventory_lot_id=1,
                    raw_material_location_id=1,
                    current_qty=20,
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
