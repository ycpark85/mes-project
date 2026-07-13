from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import BigInteger, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

import app.models  # noqa: F401
from app.db.base import Base
from app.models.drawing import Drawing
from app.models.drawing_revision import DrawingRevision
from app.models.drawing_rivision_file import DrawingRevisionFile
from app.models.lot import Lot
from app.models.lot_step import LotStep
from app.models.order_line import OrderLine
from app.models.order_line_plan_history import OrderLinePlanHistory
from app.models.partner import Partner
from app.models.process import Process
from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.product_inventory_lot import ProductInventoryLot
from app.models.product_inventory_movement import ProductInventoryMovement
from app.models.routing_template import RoutingTemplate
from app.models.routing_template_step import RoutingTemplateStep
from app.models.shipment_line import ShipmentLine
from app.schemas.order_line import (
    OrderLineBulkCommitRequest,
    OrderLineBulkCommitRowChoice,
    OrderLineBulkImportRowIn,
    OrderLineCreate,
    OrderLineFulfillmentPlanUpdate,
    OrderLineShortCloseRequest,
    OrderLineUpdate,
)
from app.schemas.order_line_detail import OrderLineDetailUpdate
from app.services.order_line_cancel_service import cancel_order_line_status
from app.services.order_line_base_lot_service import create_base_lot_from_plan
from app.services.order_line_creation_service import create_order_line_with_policy
from app.services.order_line_delete_service import delete_order_line_group
from app.services.order_line_detail_query import get_order_line_detail_dto
from app.services.order_line_detail_update_service import update_order_line_detail_fields
from app.services.order_line_lot_context_query import get_lot_create_context_dto
from app.services.order_line_list_query import list_order_lines_for_grid
from app.services.order_line_plan_service import update_order_line_fulfillment_plan_config
from app.services.order_line_response_builder import build_order_line_out, get_order_line_out_by_id
from app.services.order_line_short_close_service import short_close_order_line_status
from app.services.order_line_update_service import update_order_line_fields
from app.services.bulk.order_line_bulk_service import order_line_bulk_service


@compiles(BigInteger, "sqlite")
def _compile_big_integer_for_sqlite(_type, compiler, **kw):
    return "INTEGER"


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(_type, compiler, **kw):
    return "JSON"


TEST_TABLE_NAMES = [
    "partner",
    "drawing",
    "drawing_revision",
    "drawing_revision_file",
    "routing_template",
    "process",
    "routing_template_step",
    "product",
    "product_inventory",
    "product_inventory_lot",
    "order_line",
    "lot",
    "lot_step",
    "order_line_plan_history",
    "shipment_line",
    "inspection_schedule",
    "inspection_result",
    "defect_type",
    "inspection_defect",
    "inspection_defect_attachment",
    "product_inventory_movement",
    "shipment_coa",
    "inspection_certificate",
    "outsource_work_instruction",
    "outsource_work_instruction_item",
    "outsource_work_group",
    "outsource_work_group_item",
    "outsource_purchase_order",
    "outsource_purchase_order_item",
]


class OrderLineServicesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        tables = [Base.metadata.tables[name] for name in TEST_TABLE_NAMES]
        Base.metadata.create_all(self.engine, tables=tables)

        SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()
        self._seed_base_data()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_order_line_search_uses_exact_business_numbers_and_partial_product_code(self) -> None:
        order_line = self._seed_open_order_line_without_lots()
        order_line.customer_po = "PO-CUSTOMER-001"
        self.db.commit()

        partial_order_items, _ = list_order_lines_for_grid(
            self.db, page=1, size=20, q="SO-"
        )
        exact_order_items, _ = list_order_lines_for_grid(
            self.db, page=1, size=20, q=" so-open "
        )
        partial_po_items, _ = list_order_lines_for_grid(
            self.db, page=1, size=20, q="PO-CUSTOMER"
        )
        exact_po_items, _ = list_order_lines_for_grid(
            self.db, page=1, size=20, q=" po-customer-001 "
        )
        partial_product_items, _ = list_order_lines_for_grid(
            self.db, page=1, size=20, q="001"
        )

        self.assertEqual([], partial_order_items)
        self.assertEqual([200], [item["order_line_id"] for item in exact_order_items])
        self.assertEqual([], partial_po_items)
        self.assertEqual([200], [item["order_line_id"] for item in exact_po_items])
        self.assertEqual([200], [item["order_line_id"] for item in partial_product_items])

    def test_create_order_line_without_inventory_creates_primary_lot(self) -> None:
        with patch("app.services.order_line_creation_service.refresh_order_line_snapshot") as refresh:
            order_line = create_order_line_with_policy(self.db, self._payload("SO-AUTO-LOT", 100))

        lots = self.db.execute(select(Lot).where(Lot.order_line_id == order_line.order_line_id)).scalars().all()
        histories = self.db.execute(
            select(OrderLinePlanHistory).where(OrderLinePlanHistory.order_line_id == order_line.order_line_id)
        ).scalars().all()
        shipment_lines = self.db.execute(
            select(ShipmentLine).where(ShipmentLine.order_line_id == order_line.order_line_id)
        ).scalars().all()

        self.assertEqual("CLOSED", order_line.status)
        self.assertTrue(order_line.decision_made)
        self.assertEqual("AUTO_PRODUCTION", histories[0].plan_type)
        self.assertEqual(102, histories[0].production_qty)
        self.assertEqual(1, len(lots))
        self.assertEqual(102, lots[0].lot_qty)
        self.assertEqual([], shipment_lines)
        refresh.assert_called_once_with(self.db, order_line.order_line_id)

    def test_create_order_line_with_enough_inventory_creates_stock_waiting_line(self) -> None:
        self._seed_inventory(product_id=1, qty=300)

        order_line = create_order_line_with_policy(self.db, self._payload("SO-STOCK", 100))

        lots = self.db.execute(select(Lot).where(Lot.order_line_id == order_line.order_line_id)).scalars().all()
        histories = self.db.execute(
            select(OrderLinePlanHistory).where(OrderLinePlanHistory.order_line_id == order_line.order_line_id)
        ).scalars().all()
        shipment_lines = self.db.execute(
            select(ShipmentLine).where(ShipmentLine.order_line_id == order_line.order_line_id)
        ).scalars().all()

        self.assertEqual("DONE", order_line.status)
        self.assertTrue(order_line.decision_made)
        self.assertEqual("AUTO_STOCK_SHIP", histories[0].plan_type)
        self.assertEqual(102, histories[0].stock_ship_qty)
        self.assertEqual([], lots)
        self.assertEqual(1, len(shipment_lines))
        self.assertEqual("WAITING", shipment_lines[0].status)
        self.assertEqual(102, shipment_lines[0].ship_qty)

    def test_create_order_line_with_partial_inventory_waits_for_decision(self) -> None:
        self._seed_inventory(product_id=1, qty=50)

        order_line = create_order_line_with_policy(self.db, self._payload("SO-PARTIAL", 100))

        lots = self.db.execute(select(Lot).where(Lot.order_line_id == order_line.order_line_id)).scalars().all()
        histories = self.db.execute(
            select(OrderLinePlanHistory).where(OrderLinePlanHistory.order_line_id == order_line.order_line_id)
        ).scalars().all()
        shipment_lines = self.db.execute(
            select(ShipmentLine).where(ShipmentLine.order_line_id == order_line.order_line_id)
        ).scalars().all()

        self.assertEqual("OPEN", order_line.status)
        self.assertFalse(order_line.decision_made)
        self.assertEqual("HYBRID", order_line.fulfillment_mode)
        self.assertEqual([], histories)
        self.assertEqual([], lots)
        self.assertEqual([], shipment_lines)

    def test_update_closed_order_line_due_date_syncs_only_not_started_lots(self) -> None:
        order_line = self._seed_closed_order_line_with_lots()
        new_due_date = date(2026, 2, 15)

        with patch("app.services.order_line_update_service.refresh_order_line_snapshot") as refresh:
            updated = update_order_line_fields(
                self.db,
                order_line.order_line_id,
                OrderLineUpdate(due_date=new_due_date, memo="납기 조정"),
            )

        waiting_lot = self.db.get(Lot, 101)
        started_lot = self.db.get(Lot, 102)

        self.assertEqual(new_due_date, updated.due_date)
        self.assertEqual("납기 조정", updated.memo)
        self.assertEqual(new_due_date, waiting_lot.due_date)
        self.assertEqual(date(2026, 1, 31), started_lot.due_date)
        refresh.assert_called_once_with(self.db, order_line.order_line_id)

    def test_update_closed_order_line_rejects_quantity_change(self) -> None:
        order_line = self._seed_closed_order_line_with_lots()

        with self.assertRaises(HTTPException) as ctx:
            update_order_line_fields(self.db, order_line.order_line_id, OrderLineUpdate(order_qty=200))

        self.assertEqual(409, ctx.exception.status_code)

    def test_order_line_detail_marks_flags_current_process_and_plan_timeline(self) -> None:
        order_line = self._seed_closed_order_line_with_lots()
        self.db.add(
            OrderLinePlanHistory(
                plan_history_id=100,
                order_line_id=order_line.order_line_id,
                plan_type="AUTO_PRODUCTION",
                ship_target_qty=102,
                available_inventory_qty=0,
                stock_ship_qty=0,
                production_qty=102,
                is_short_close=False,
                memo="자동 생산",
            )
        )
        self.db.flush()

        detail = get_order_line_detail_dto(self.db, order_line.order_line_id)
        lot_map = {lot.lot_no: lot for lot in detail.lots}

        self.assertEqual("IN_PROGRESS", detail.status_display)
        self.assertTrue(detail.can_edit)
        self.assertTrue(detail.can_save)
        self.assertFalse(detail.can_cancel_order)
        self.assertFalse(detail.can_create_base_lot)
        self.assertEqual("재단", lot_map["LOT-STARTED"].current_process_name)
        self.assertTrue(lot_map["LOT-STARTED"].is_editable)
        self.assertTrue(any(item.event_type == "PLAN_CONFIRMED" for item in detail.timeline))

    def test_order_line_detail_can_exclude_plan_history_for_post_action_response(self) -> None:
        order_line = self._seed_closed_order_line_with_lots()
        self.db.add(
            OrderLinePlanHistory(
                plan_history_id=101,
                order_line_id=order_line.order_line_id,
                plan_type="AUTO_PRODUCTION",
                ship_target_qty=102,
                available_inventory_qty=0,
                stock_ship_qty=0,
                production_qty=102,
                is_short_close=False,
            )
        )
        self.db.flush()

        detail = get_order_line_detail_dto(self.db, order_line.order_line_id, include_plan_history=False)

        self.assertFalse(any(item.event_type == "PLAN_CONFIRMED" for item in detail.timeline))

    def test_order_line_detail_marks_canceled_order_as_not_actionable(self) -> None:
        order_line = self._seed_closed_order_line_with_lots()
        order_line.status = "CANCELED"
        for lot in self.db.execute(select(Lot).where(Lot.order_line_id == order_line.order_line_id)).scalars():
            lot.status = "CANCELED"
        self.db.flush()

        detail = get_order_line_detail_dto(self.db, order_line.order_line_id, include_plan_history=False)

        self.assertEqual("CANCELED", detail.status_display)
        self.assertFalse(detail.can_edit)
        self.assertFalse(detail.can_save)
        self.assertFalse(detail.can_cancel_order)
        self.assertFalse(detail.can_create_base_lot)
        self.assertTrue(all(not lot.is_editable for lot in detail.lots))
        self.assertTrue(all(not lot.can_cancel for lot in detail.lots))
        self.assertTrue(all(lot.can_create_rework for lot in detail.lots))
        self.assertTrue(any(item.event_type == "ORDER_CANCELED" for item in detail.timeline))

    def test_cancel_order_line_without_lots_marks_canceled(self) -> None:
        order_line = self._seed_open_order_line_without_lots()

        canceled = cancel_order_line_status(self.db, order_line.order_line_id)

        self.assertEqual("CANCELED", canceled.status)
        self.assertEqual("CANCELED", self.db.get(OrderLine, order_line.order_line_id).status)

    def test_cancel_order_line_rejects_non_canceled_lot(self) -> None:
        order_line = self._seed_closed_order_line_with_lots()

        with self.assertRaises(HTTPException) as ctx:
            cancel_order_line_status(self.db, order_line.order_line_id)

        self.assertEqual(409, ctx.exception.status_code)
        self.assertEqual("CLOSED", self.db.get(OrderLine, order_line.order_line_id).status)

    def test_cancel_order_line_allows_when_all_lots_are_canceled(self) -> None:
        order_line = self._seed_closed_order_line_with_lots()
        for lot in self.db.execute(select(Lot).where(Lot.order_line_id == order_line.order_line_id)).scalars():
            lot.status = "CANCELED"
        self.db.flush()

        canceled = cancel_order_line_status(self.db, order_line.order_line_id)
        detail = get_order_line_detail_dto(self.db, order_line.order_line_id, include_plan_history=False)

        self.assertEqual("CANCELED", canceled.status)
        self.assertFalse(detail.can_cancel_order)
        self.assertTrue(any(item.event_type == "ORDER_CANCELED" for item in detail.timeline))

    def test_delete_order_line_group_removes_same_order_number_rows_and_children(self) -> None:
        self._seed_deletable_order_group()

        result = delete_order_line_group(self.db, 300)

        self.assertEqual(
            {
                "success": True,
                "order_no": "SO-DELETE",
                "deleted_order_line_count": 2,
                "deleted_lot_count": 2,
                "deleted_shipment_line_count": 1,
            },
            result,
        )
        self.assertEqual(0, self._count(OrderLine, OrderLine.order_no == "SO-DELETE"))
        self.assertEqual(0, self._count(Lot, Lot.order_line_id.in_([300, 301])))
        self.assertEqual(0, self._count(LotStep, LotStep.lot_id.in_([301, 302])))
        self.assertEqual(0, self._count(OrderLinePlanHistory, OrderLinePlanHistory.order_line_id.in_([300, 301])))
        self.assertEqual(0, self._count(ShipmentLine, ShipmentLine.order_line_id.in_([300, 301])))

    def test_delete_order_line_group_rejects_progressed_lot(self) -> None:
        self._seed_deletable_order_group()
        self.db.get(Lot, 301).status = "DONE"
        self.db.flush()

        with self.assertRaises(HTTPException) as ctx:
            delete_order_line_group(self.db, 300)

        self.assertEqual(409, ctx.exception.status_code)
        self.assertIn("진행/완료 LOT 1건", str(ctx.exception.detail))
        self.assertEqual(2, self._count(OrderLine, OrderLine.order_no == "SO-DELETE"))
        self.assertEqual(2, self._count(Lot, Lot.order_line_id.in_([300, 301])))

    def test_create_base_lot_from_plan_creates_planned_lot_and_steps(self) -> None:
        order_line = self._seed_open_decision_made_order_line()
        self.db.add(
            OrderLinePlanHistory(
                plan_history_id=400,
                order_line_id=order_line.order_line_id,
                plan_type="PARTIAL_STOCK_PLUS_PRODUCTION",
                ship_target_qty=102,
                available_inventory_qty=20,
                stock_ship_qty=20,
                production_qty=82,
                is_short_close=False,
            )
        )
        self.db.flush()

        with patch("app.services.order_line_creation_service.refresh_order_line_snapshot") as refresh:
            result = create_base_lot_from_plan(self.db, order_line.order_line_id)

        created_lot = self.db.get(Lot, result.created_lot_id)
        created_steps = self.db.execute(
            select(LotStep).where(LotStep.lot_id == result.created_lot_id)
        ).scalars().all()

        self.assertEqual(order_line.order_line_id, result.order_line_id)
        self.assertEqual(82, result.planned_production_qty)
        self.assertEqual(82, result.created_lot_qty)
        self.assertEqual("CLOSED", result.order_status)
        self.assertEqual("CLOSED", order_line.status)
        self.assertEqual(82, created_lot.lot_qty)
        self.assertEqual(1, len(created_steps))
        self.assertEqual("WAITING", created_steps[0].status)
        refresh.assert_called_once_with(self.db, order_line.order_line_id)

    def test_create_base_lot_from_plan_rejects_missing_decision(self) -> None:
        order_line = self._seed_open_order_line_without_lots()

        with self.assertRaises(HTTPException) as ctx:
            create_base_lot_from_plan(self.db, order_line.order_line_id)

        self.assertEqual(409, ctx.exception.status_code)
        self.assertEqual(0, self._count(Lot, Lot.order_line_id == order_line.order_line_id))

    def test_lot_create_context_includes_drawing_files_and_primary_lot_candidates(self) -> None:
        order_line = self._seed_closed_order_line_with_lots()
        self.db.get(Lot, 102).status = "DONE"
        self.db.flush()

        context = get_lot_create_context_dto(self.db, order_line.order_line_id)
        candidates = {candidate.lot_no: candidate for candidate in context.primary_lot_candidates}

        self.assertEqual(order_line.order_line_id, context.order_line_id)
        self.assertEqual("Customer", context.partner_name)
        self.assertEqual("P-001", context.product_code)
        self.assertEqual(1, context.drawing.drawing_id)
        self.assertEqual("D-001", context.drawing.drawing_no)
        self.assertEqual(1, context.drawing.current_revision_id)
        self.assertEqual("A", context.drawing.current_revision_no)
        self.assertEqual("drawing.pdf", context.drawing.drawing_file_name)
        self.assertEqual("original.ai", context.drawing.original_file_name)
        self.assertEqual("plate.pdf", context.drawing.plate_file_name)
        self.assertFalse(candidates["LOT-WAITING"].can_create_rework)
        self.assertTrue(candidates["LOT-STARTED"].can_create_rework)

    def test_update_order_line_detail_fields_updates_due_qty_memo_and_syncs_waiting_lots(self) -> None:
        order_line = self._seed_closed_order_line_with_lots()
        new_due_date = date(2026, 2, 20)

        with patch("app.services.order_line_update_service.refresh_order_line_snapshot") as refresh:
            updated = update_order_line_detail_fields(
                self.db,
                order_line.order_line_id,
                OrderLineDetailUpdate(
                    due_date=new_due_date,
                    order_qty=120,
                    memo="detail memo",
                ),
            )

        waiting_lot = self.db.get(Lot, 101)
        started_lot = self.db.get(Lot, 102)

        self.assertEqual(new_due_date, updated.due_date)
        self.assertEqual(120, updated.order_qty)
        self.assertEqual("detail memo", updated.memo)
        self.assertEqual(new_due_date, waiting_lot.due_date)
        self.assertEqual(date(2026, 1, 31), started_lot.due_date)
        refresh.assert_called_once_with(self.db, order_line.order_line_id)

    def test_update_order_line_detail_fields_rejects_done_order_line(self) -> None:
        order_line = self._seed_closed_order_line_with_lots()
        order_line.status = "DONE"
        self.db.flush()

        with self.assertRaises(HTTPException) as ctx:
            update_order_line_detail_fields(
                self.db,
                order_line.order_line_id,
                OrderLineDetailUpdate(
                    due_date=date(2026, 2, 20),
                    order_qty=120,
                    memo="blocked",
                ),
            )

        self.assertEqual(409, ctx.exception.status_code)

    def test_short_close_order_line_status_marks_done_and_appends_remaining_qty_memo(self) -> None:
        order_line = self._seed_closed_order_line_with_lots()

        updated = short_close_order_line_status(
            self.db,
            order_line.order_line_id,
            OrderLineShortCloseRequest(memo="customer accepted shortage"),
        )

        self.assertEqual("DONE", updated.status)
        self.assertIn("[SHORT_CLOSE] remaining_ship_qty=102", updated.memo)
        self.assertIn("customer accepted shortage", updated.memo)

    def test_short_close_order_line_status_rejects_when_no_remaining_ship_qty(self) -> None:
        order_line = self._seed_closed_order_line_with_lots()
        self.db.add(
            ProductInventoryMovement(
                inventory_movement_id=100,
                product_id=1,
                product_inventory_lot_id=None,
                stock_lot_no=None,
                movement_type="SHIP_OUT",
                qty=-102,
                balance_after=0,
                order_line_id=order_line.order_line_id,
            )
        )
        self.db.flush()

        with self.assertRaises(HTTPException) as ctx:
            short_close_order_line_status(
                self.db,
                order_line.order_line_id,
                OrderLineShortCloseRequest(memo="no shortage"),
            )

        self.assertEqual(409, ctx.exception.status_code)
        self.assertEqual("CLOSED", order_line.status)

    def test_update_order_line_fulfillment_plan_config_saves_production_plan(self) -> None:
        order_line = self._seed_open_order_line_without_lots()

        updated = update_order_line_fulfillment_plan_config(
            self.db,
            order_line_id=order_line.order_line_id,
            payload=OrderLineFulfillmentPlanUpdate(
                fulfillment_mode="PRODUCTION_FIRST",
                production_policy="ALLOW_STOCK_BUILD",
                extra_production_qty=5,
            ),
        )

        shipment_lines = self.db.execute(
            select(ShipmentLine).where(ShipmentLine.order_line_id == order_line.order_line_id)
        ).scalars().all()

        self.assertTrue(updated.decision_made)
        self.assertEqual("PRODUCTION_FIRST", updated.fulfillment_mode)
        self.assertEqual("ALLOW_STOCK_BUILD", updated.production_policy)
        self.assertEqual(5, updated.extra_production_qty)
        self.assertEqual("OPEN", updated.status)
        self.assertEqual([], shipment_lines)

    def test_update_order_line_fulfillment_plan_config_creates_stock_waiting_when_no_production_needed(self) -> None:
        order_line = self._seed_open_order_line_without_lots()
        self._seed_inventory(product_id=1, qty=300)

        updated = update_order_line_fulfillment_plan_config(
            self.db,
            order_line_id=order_line.order_line_id,
            payload=OrderLineFulfillmentPlanUpdate(
                fulfillment_mode="INVENTORY_FIRST",
                production_policy="INVENTORY_ONLY_CLOSE",
                extra_production_qty=0,
            ),
        )

        shipment_lines = self.db.execute(
            select(ShipmentLine).where(ShipmentLine.order_line_id == order_line.order_line_id)
        ).scalars().all()

        self.assertTrue(updated.decision_made)
        self.assertEqual("INVENTORY_FIRST", updated.fulfillment_mode)
        self.assertEqual("INVENTORY_ONLY_CLOSE", updated.production_policy)
        self.assertEqual(0, updated.extra_production_qty)
        self.assertEqual("CLOSED", updated.status)
        self.assertEqual(1, len(shipment_lines))
        self.assertEqual("WAITING", shipment_lines[0].status)
        self.assertEqual(102, shipment_lines[0].ship_qty)

    def test_update_order_line_fulfillment_plan_config_rejects_done_order_line(self) -> None:
        order_line = self._seed_open_order_line_without_lots()
        order_line.status = "DONE"
        self.db.flush()

        with self.assertRaises(HTTPException) as ctx:
            update_order_line_fulfillment_plan_config(
                self.db,
                order_line_id=order_line.order_line_id,
                payload=OrderLineFulfillmentPlanUpdate(
                    fulfillment_mode="PRODUCTION_FIRST",
                    production_policy="ORDER_ONLY",
                    extra_production_qty=10,
                ),
            )

        self.assertEqual(409, ctx.exception.status_code)

    def test_commit_order_line_bulk_creates_group_and_applies_product_name_change(self) -> None:
        payload = OrderLineBulkCommitRequest(
            items=[
                OrderLineBulkImportRowIn(
                    row_number=1,
                    erp_order_no="2026/01/10 - 1",
                    product_code="P-001",
                    partner_name="Customer",
                    erp_product_display_name="Updated Product [Spec A]",
                    order_qty_text="10",
                    due_date_text="2026/01/31",
                    remark="bulk memo",
                ),
                OrderLineBulkImportRowIn(
                    row_number=2,
                    erp_order_no="2026/01/10 - 1",
                    product_code="P-001",
                    partner_name="Customer",
                    erp_product_display_name="Updated Product [Spec A]",
                    order_qty_text="20",
                    due_date_text="2026/01/31",
                    remark="bulk memo",
                ),
            ],
            row_choices=[
                OrderLineBulkCommitRowChoice(row_number=1, apply_product_name_change=True),
                OrderLineBulkCommitRowChoice(row_number=2, apply_product_name_change=True),
            ],
        )

        with patch("app.services.order_line_creation_service.refresh_order_line_snapshot"):
            result = order_line_bulk_service.commit_bulk(self.db, payload)

        created_order_lines = (
            self.db.execute(
                select(OrderLine).where(OrderLine.order_no == "2026/01/10 - 1").order_by(OrderLine.line_no.asc())
            )
            .scalars()
            .all()
        )
        product = self.db.get(Product, 1)

        self.assertEqual(1, result.success_group_count)
        self.assertEqual(0, result.failure_group_count)
        self.assertEqual(2, len(result.groups[0].created_order_line_ids))
        self.assertEqual([1, 2], [order_line.line_no for order_line in created_order_lines])
        self.assertEqual([10, 20], [order_line.order_qty for order_line in created_order_lines])
        self.assertTrue(all(order_line.memo == "bulk memo" for order_line in created_order_lines))
        self.assertEqual("Updated Product", product.product_name)
        self.assertEqual("Spec A", product.product_spec)

    def test_commit_order_line_bulk_rejects_conflicting_product_name_change_choices(self) -> None:
        payload = OrderLineBulkCommitRequest(
            items=[
                OrderLineBulkImportRowIn(
                    row_number=1,
                    erp_order_no="2026/01/11 - 1",
                    product_code="P-001",
                    partner_name="Customer",
                    erp_product_display_name="Updated Product A",
                    order_qty_text="10",
                    due_date_text="2026/01/31",
                    remark=None,
                ),
                OrderLineBulkImportRowIn(
                    row_number=2,
                    erp_order_no="2026/01/11 - 1",
                    product_code="P-001",
                    partner_name="Customer",
                    erp_product_display_name="Updated Product B",
                    order_qty_text="20",
                    due_date_text="2026/01/31",
                    remark=None,
                ),
            ],
            row_choices=[
                OrderLineBulkCommitRowChoice(row_number=1, apply_product_name_change=True),
                OrderLineBulkCommitRowChoice(row_number=2, apply_product_name_change=True),
            ],
        )

        result = order_line_bulk_service.commit_bulk(self.db, payload)

        self.assertEqual(0, result.success_group_count)
        self.assertEqual(1, result.failure_group_count)
        self.assertEqual("ERROR", result.groups[0].status)
        self.assertIn("서로 다른 품목명 변경", result.groups[0].message)
        self.assertEqual(0, self._count(OrderLine, OrderLine.order_no == "2026/01/11 - 1"))

    def test_build_order_line_out_includes_display_fields_and_plan_summary(self) -> None:
        order_line = self._seed_closed_order_line_with_lots()
        history = OrderLinePlanHistory(
            plan_history_id=500,
            order_line_id=order_line.order_line_id,
            plan_type="AUTO_PRODUCTION",
            ship_target_qty=102,
            available_inventory_qty=0,
            stock_ship_qty=0,
            production_qty=102,
            is_short_close=False,
        )
        self.db.add(history)
        self.db.flush()

        out = build_order_line_out(self.db, order_line, plan_history=history)

        self.assertEqual("Customer", out.partner_name)
        self.assertEqual("P-001", out.product_code)
        self.assertEqual(order_line.product.product_name, out.product_name)
        self.assertEqual("AUTO_PRODUCTION", out.plan_type)
        self.assertIsNotNone(out.plan_type_display)

    def test_get_order_line_out_by_id_rejects_inactive_or_missing_order_line(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            get_order_line_out_by_id(self.db, 999999)

        self.assertEqual(404, ctx.exception.status_code)

    def _payload(self, order_no: str, order_qty: int) -> OrderLineCreate:
        return OrderLineCreate(
            order_no=order_no,
            line_no=1,
            partner_id=1,
            product_id=1,
            order_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            order_qty=order_qty,
            uom="EA",
        )

    def _seed_base_data(self) -> None:
        self.db.add_all(
            [
                Partner(
                    partner_id=1,
                    partner_type="CUSTOMER",
                    name="Customer",
                    business_no="C-001",
                    is_active=True,
                ),
                Drawing(
                    drawing_id=1,
                    drawing_no="D-001",
                    current_revision_id=1,
                    is_active=True,
                ),
                DrawingRevision(
                    revision_id=1,
                    drawing_id=1,
                    rev_no="A",
                    file_uri="/drawings/D-001-A.pdf",
                ),
                DrawingRevisionFile(
                    revision_file_id=1,
                    revision_id=1,
                    file_kind="DRAWING",
                    file_uri="/drawings/drawing.pdf",
                    original_filename="drawing.pdf",
                    content_type="application/pdf",
                ),
                DrawingRevisionFile(
                    revision_file_id=2,
                    revision_id=1,
                    file_kind="ORIGINAL",
                    file_uri="/drawings/original.ai",
                    original_filename="original.ai",
                    content_type="application/postscript",
                ),
                DrawingRevisionFile(
                    revision_file_id=3,
                    revision_id=1,
                    file_kind="PLATE",
                    file_uri="/drawings/plate.pdf",
                    original_filename="plate.pdf",
                    content_type="application/pdf",
                ),
                RoutingTemplate(
                    routing_template_id=1,
                    template_code="RT-001",
                    template_name="기본 라우팅",
                    is_active=True,
                ),
                Process(
                    process_id=1,
                    process_code="CUT",
                    process_name="재단",
                    process_type="INTERNAL",
                    is_active=True,
                ),
                RoutingTemplateStep(
                    routing_template_step_id=1,
                    routing_template_id=1,
                    step_seq=10,
                    process_id=1,
                    default_process_type="INTERNAL",
                    is_active=True,
                ),
                Product(
                    product_id=1,
                    product_code="P-001",
                    product_name="제품",
                    uom="EA",
                    drawing_id=1,
                    routing_template_id=1,
                    is_active=True,
                ),
            ]
        )
        self.db.commit()

    def _seed_inventory(self, *, product_id: int, qty: int) -> None:
        self.db.add_all(
            [
                ProductInventory(
                    product_inventory_id=product_id,
                    product_id=product_id,
                    current_qty=qty,
                ),
                ProductInventoryLot(
                    product_inventory_lot_id=product_id,
                    product_id=product_id,
                    lot_no=f"STOCK-{product_id}",
                    current_qty=qty,
                ),
            ]
        )
        self.db.flush()

    def _seed_closed_order_line_with_lots(self) -> OrderLine:
        order_line = OrderLine(
            order_line_id=100,
            order_no="SO-CLOSED",
            line_no=1,
            partner_id=1,
            product_id=1,
            order_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            order_qty=100,
            uom="EA",
            status="CLOSED",
            is_active=True,
        )
        self.db.add(order_line)
        self.db.add_all(
            [
                Lot(
                    lot_id=101,
                    lot_no="LOT-WAITING",
                    order_line_id=100,
                    product_id=1,
                    lot_qty=100,
                    uom="EA",
                    created_date=date(2026, 1, 2),
                    due_date=date(2026, 1, 31),
                    status="WAITING",
                ),
                Lot(
                    lot_id=102,
                    lot_no="LOT-STARTED",
                    order_line_id=100,
                    product_id=1,
                    lot_qty=100,
                    uom="EA",
                    created_date=date(2026, 1, 2),
                    due_date=date(2026, 1, 31),
                    status="WAITING",
                ),
                LotStep(
                    lot_step_id=101,
                    lot_id=101,
                    step_seq=10,
                    process_id=1,
                    process_code="CUT",
                    process_name="재단",
                    process_type="INTERNAL",
                    status="WAITING",
                ),
                LotStep(
                    lot_step_id=102,
                    lot_id=102,
                    step_seq=10,
                    process_id=1,
                    process_code="CUT",
                    process_name="재단",
                    process_type="INTERNAL",
                    status="IN_PROGRESS",
                ),
            ]
        )
        self.db.flush()
        return order_line

    def _seed_open_order_line_without_lots(self) -> OrderLine:
        order_line = OrderLine(
            order_line_id=200,
            order_no="SO-OPEN",
            line_no=1,
            partner_id=1,
            product_id=1,
            order_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            order_qty=100,
            uom="EA",
            status="OPEN",
            is_active=True,
        )
        self.db.add(order_line)
        self.db.flush()
        return order_line

    def _seed_open_decision_made_order_line(self) -> OrderLine:
        order_line = OrderLine(
            order_line_id=400,
            order_no="SO-BASE-LOT",
            line_no=1,
            partner_id=1,
            product_id=1,
            order_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            order_qty=100,
            uom="EA",
            status="OPEN",
            is_active=True,
            decision_made=True,
            fulfillment_mode="INVENTORY_FIRST",
            production_policy="ORDER_ONLY",
        )
        self.db.add(order_line)
        self.db.flush()
        return order_line

    def _seed_deletable_order_group(self) -> None:
        self.db.add_all(
            [
                OrderLine(
                    order_line_id=300,
                    order_no="SO-DELETE",
                    line_no=1,
                    partner_id=1,
                    product_id=1,
                    order_date=date(2026, 1, 1),
                    due_date=date(2026, 1, 31),
                    order_qty=100,
                    uom="EA",
                    status="OPEN",
                    is_active=True,
                ),
                OrderLine(
                    order_line_id=301,
                    order_no="SO-DELETE",
                    line_no=2,
                    partner_id=1,
                    product_id=1,
                    order_date=date(2026, 1, 1),
                    due_date=date(2026, 1, 31),
                    order_qty=50,
                    uom="EA",
                    status="OPEN",
                    is_active=True,
                ),
                Lot(
                    lot_id=301,
                    lot_no="LOT-DELETE-1",
                    order_line_id=300,
                    product_id=1,
                    lot_qty=100,
                    uom="EA",
                    created_date=date(2026, 1, 2),
                    due_date=date(2026, 1, 31),
                    status="WAITING",
                ),
                Lot(
                    lot_id=302,
                    lot_no="LOT-DELETE-2",
                    order_line_id=301,
                    product_id=1,
                    lot_qty=50,
                    uom="EA",
                    created_date=date(2026, 1, 2),
                    due_date=date(2026, 1, 31),
                    status="CANCELED",
                ),
                LotStep(
                    lot_step_id=301,
                    lot_id=301,
                    step_seq=10,
                    process_id=1,
                    process_code="CUT",
                    process_name="?щ떒",
                    process_type="INTERNAL",
                    status="WAITING",
                ),
                LotStep(
                    lot_step_id=302,
                    lot_id=302,
                    step_seq=10,
                    process_id=1,
                    process_code="CUT",
                    process_name="?щ떒",
                    process_type="INTERNAL",
                    status="WAITING",
                ),
                OrderLinePlanHistory(
                    plan_history_id=300,
                    order_line_id=300,
                    plan_type="AUTO_PRODUCTION",
                    ship_target_qty=102,
                    available_inventory_qty=0,
                    stock_ship_qty=0,
                    production_qty=102,
                    is_short_close=False,
                ),
                ShipmentLine(
                    shipment_line_id=300,
                    order_line_id=300,
                    product_id=1,
                    product_inventory_lot_id=None,
                    lot_id=301,
                    inspection_result_id=None,
                    source_type="STOCK",
                    status="WAITING",
                    ship_qty=10,
                    shipped_qty=0,
                ),
            ]
        )
        self.db.flush()

    def _count(self, model, *conditions) -> int:
        stmt = select(func.count()).select_from(model)
        if conditions:
            stmt = stmt.where(*conditions)
        return int(self.db.execute(stmt).scalar_one() or 0)


if __name__ == "__main__":
    unittest.main()
