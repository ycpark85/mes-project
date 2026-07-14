from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_group_item import OutsourceWorkGroupItem
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.models.partner import Partner
from app.models.product import Product
from app.models.routing_template import RoutingTemplate
from app.services import bohyun_outsource_service as service


TEST_TABLE_NAMES = [
    "partner",
    "routing_template",
    "product",
    "order_line",
    "lot",
    "outsource_work_instruction",
    "outsource_work_group",
    "outsource_work_group_item",
]


class BohyunOutsourceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        tables = [Base.metadata.tables[name] for name in TEST_TABLE_NAMES]
        Base.metadata.create_all(self.engine, tables=tables)

        SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()
        self._seed_base_data()

        self.refresh_patch = patch.object(
            service,
            "refresh_order_line_snapshots_for_work_groups",
            autospec=True,
        )
        self.refresh_mock = self.refresh_patch.start()

    def tearDown(self) -> None:
        self.refresh_patch.stop()
        self.db.close()
        self.engine.dispose()

    def test_inbound_waiting_group_sets_vendor_received(self) -> None:
        self._add_work_group(group_id=1, status=None)
        now = datetime(2026, 7, 13, 2, 0, tzinfo=timezone.utc)

        with patch.object(service, "utc_now", return_value=now) as utc_now_mock:
            service.inbound_bohyun_outsource_group(self.db, 1)

        work_group = self.db.get(OutsourceWorkGroup, 1)
        self.assertEqual(service.BOHYUN_DB_STATUS_VENDOR_RECEIVED, work_group.status)
        self.assertIsNotNone(work_group.vendor_received_at)
        utc_now_mock.assert_called_once_with()
        self.refresh_mock.assert_called_once_with(self.db, {1})

    def test_inbound_rejects_already_work_done_group(self) -> None:
        self._add_work_group(group_id=1, status=service.BOHYUN_DB_STATUS_WORK_DONE)

        with self.assertRaises(HTTPException) as error:
            service.inbound_bohyun_outsource_group(self.db, 1)

        self.assertEqual(409, error.exception.status_code)

    def test_work_done_requires_inbounded_group(self) -> None:
        self._add_work_group(group_id=1, status=None)

        with self.assertRaises(HTTPException) as error:
            service.complete_bohyun_outsource_group_work(
                self.db,
                1,
                work_done_sheet_qty=10,
                outsource_processing_fee=Decimal("1000.00"),
                remark="done",
            )

        self.assertEqual(409, error.exception.status_code)

    def test_work_done_sets_group_status_and_item_output_qty(self) -> None:
        self._add_work_group(
            group_id=1,
            status=service.BOHYUN_DB_STATUS_VENDOR_RECEIVED,
            cuts_per_sheet=3,
        )

        now = datetime(2026, 7, 13, 2, 0, tzinfo=timezone.utc)
        with patch.object(service, "utc_now", return_value=now) as utc_now_mock:
            service.complete_bohyun_outsource_group_work(
                self.db,
                1,
                work_done_sheet_qty=7,
                outsource_processing_fee=Decimal("1234.00"),
                remark="normal",
            )

        work_group = self.db.get(OutsourceWorkGroup, 1)
        group_item = self.db.get(OutsourceWorkGroupItem, 1001)
        self.assertEqual(service.BOHYUN_DB_STATUS_WORK_DONE, work_group.status)
        self.assertEqual(7, work_group.work_done_sheet_qty)
        self.assertEqual(Decimal("1234.00"), work_group.outsource_processing_fee)
        self.assertEqual("normal", work_group.work_done_remark)
        self.assertEqual(21, group_item.actual_output_qty)
        self.assertIsNotNone(work_group.work_done_at)
        utc_now_mock.assert_called_once_with()

    def test_ship_requires_work_done_group(self) -> None:
        self._add_work_group(group_id=1, status=service.BOHYUN_DB_STATUS_VENDOR_RECEIVED)

        with self.assertRaises(HTTPException) as error:
            service.ship_bohyun_outsource_groups(self.db, [1])

        self.assertEqual(409, error.exception.status_code)

    def test_ship_sets_shipped_status(self) -> None:
        self._add_work_group(group_id=1, status=service.BOHYUN_DB_STATUS_WORK_DONE)
        now = datetime(2026, 7, 13, 2, 0, tzinfo=timezone.utc)

        with patch.object(service, "utc_now", return_value=now) as utc_now_mock:
            service.ship_bohyun_outsource_groups(self.db, [1])

        work_group = self.db.get(OutsourceWorkGroup, 1)
        self.assertEqual(service.BOHYUN_DB_STATUS_SHIPPED, work_group.status)
        self.assertIsNotNone(work_group.shipped_at)
        utc_now_mock.assert_called_once_with()
        self.refresh_mock.assert_called_once_with(self.db, [1])

    def test_canceled_group_cannot_be_processed(self) -> None:
        self._add_work_group(group_id=1, status=service.OUTSOURCE_WORK_GROUP_STATUS_CANCELED)

        with self.assertRaises(HTTPException) as error:
            service.inbound_bohyun_outsource_group(self.db, 1)

        self.assertEqual(409, error.exception.status_code)

    def test_list_default_excludes_shipped_and_canceled_groups(self) -> None:
        self._add_work_group(group_id=1, status=None)
        self._add_work_group(group_id=2, status=service.BOHYUN_DB_STATUS_WORK_DONE)
        self._add_work_group(group_id=3, status=service.BOHYUN_DB_STATUS_SHIPPED)
        self._add_work_group(group_id=4, status=service.OUTSOURCE_WORK_GROUP_STATUS_CANCELED)

        result = service.list_bohyun_outsource_groups(self.db)

        self.assertEqual([1, 2], [item.outsource_work_group_id for item in result.items])
        self.assertEqual(2, result.total_count)

    def test_list_uses_bounded_queries_for_multiple_groups(self) -> None:
        self._add_work_group(group_id=1, status=None)
        self._add_work_group(group_id=2, status=service.BOHYUN_DB_STATUS_WORK_DONE)
        statement_count = 0

        def count_statement(*_args) -> None:
            nonlocal statement_count
            statement_count += 1

        event.listen(self.engine, "before_cursor_execute", count_statement)
        try:
            result = service.list_bohyun_outsource_groups(self.db)
        finally:
            event.remove(self.engine, "before_cursor_execute", count_statement)

        self.assertEqual(2, len(result.items))
        self.assertEqual(3, statement_count)

    def test_list_paginates_after_target_filtering(self) -> None:
        self._add_work_group(group_id=1, status=None, processing_fee=Decimal("1000"))
        self._add_work_group(
            group_id=2,
            status=service.BOHYUN_DB_STATUS_WORK_DONE,
            processing_fee=Decimal("2000"),
        )

        result = service.list_bohyun_outsource_groups(
            self.db,
            page=2,
            size=1,
        )

        self.assertEqual(2, result.total_count)
        self.assertEqual(2, result.page)
        self.assertEqual(1, result.size)
        self.assertEqual([2], [item.outsource_work_group_id for item in result.items])
        self.assertEqual(Decimal("3000"), result.processing_fee_total)

    def test_list_routes_print_products_to_print_group(self) -> None:
        routing_template = self.db.get(RoutingTemplate, 1)
        routing_template.template_name = "인쇄"
        self.db.commit()
        self._add_work_group(group_id=1, status=None, process_type="CUT")
        self._add_work_group(group_id=2, status=None, process_type="PRINT")

        result = service.list_bohyun_outsource_groups(self.db)

        self.assertEqual([2], [item.outsource_work_group_id for item in result.items])

    def _seed_base_data(self) -> None:
        self.db.add_all(
            [
                Partner(
                    partner_id=1,
                    partner_type="VENDOR",
                    name="Bohyun",
                    business_no="V-001",
                    is_active=True,
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
                    template_code="CUT_ONLY",
                    template_name="CUT_ONLY",
                    is_active=True,
                ),
                Product(
                    product_id=1,
                    product_code="P-001",
                    product_name="Product 1",
                    uom="EA",
                    drawing_id=1,
                    routing_template_id=1,
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
                Lot(
                    lot_id=1,
                    lot_no="LOT-001",
                    order_line_id=1,
                    product_id=1,
                    lot_qty=100,
                    uom="EA",
                    created_date=date(2026, 1, 2),
                    due_date=date(2026, 1, 10),
                    status="WAITING",
                ),
                OutsourceWorkInstruction(
                    outsource_work_instruction_id=1,
                    instruction_no="OWI-001",
                    instruction_date=date(2026, 1, 3),
                    process_type="CUT",
                    partner_id=1,
                    is_bundle=False,
                ),
            ]
        )
        self.db.commit()

    def _add_work_group(
        self,
        *,
        group_id: int,
        status: str | None,
        cuts_per_sheet: int = 1,
        processing_fee: Decimal | None = None,
        process_type: str = "CUT",
    ) -> None:
        self.db.add(
            OutsourceWorkGroup(
                outsource_work_group_id=group_id,
                outsource_work_instruction_id=1,
                group_seq=f"G-{group_id:03d}",
                process_type=process_type,
                is_bundle=False,
                sheet_qty=100,
                sheet_cut_count=1,
                status=status,
                outsource_processing_fee=processing_fee,
                representative_lot_id=1,
            )
        )
        self.db.add(
            OutsourceWorkGroupItem(
                outsource_work_group_item_id=1000 + group_id,
                outsource_work_group_id=group_id,
                lot_id=1,
                cuts_per_sheet=cuts_per_sheet,
                expected_output_qty=100 * cuts_per_sheet,
            )
        )
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
