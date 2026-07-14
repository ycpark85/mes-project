from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.models.drawing import Drawing
from app.models.inspection_schedule import InspectionSchedule
from app.models.lot import Lot
from app.models.order_line import OrderLine
from app.models.outsource_work_group import OutsourceWorkGroup
from app.models.outsource_work_instruction import OutsourceWorkInstruction
from app.models.outsource_work_instruction_file import OutsourceWorkInstructionFile
from app.models.partner import Partner
from app.models.product import Product
from app.models.routing_template import RoutingTemplate
from app.services import outsource_work_instruction_file_service as file_service
from app.services.outsource_work_instruction_file_service import (
    get_inspection_schedule_plate_data_file,
    get_work_group_plate_data_file,
    save_plate_data_file,
    save_plate_data_stream,
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
    "outsource_work_instruction",
    "outsource_work_instruction_file",
    "outsource_work_group",
    "inspection_schedule",
]


class OutsourceWorkInstructionFileServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        tables = [Base.metadata.tables[name] for name in TEST_TABLE_NAMES]
        Base.metadata.create_all(self.engine, tables=tables)

        SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_save_plate_data_file_writes_file_to_dated_folder(self) -> None:
        uploaded_at = datetime(2026, 1, 1, 16, 4, 5, tzinfo=timezone.utc)

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch.object(file_service.settings, "PLATE_DATA_STORAGE_ROOT", tmpdir),
                patch.object(file_service.settings, "PLATE_DATA_ALLOWED_EXT", {".pdf"}),
                patch.object(file_service.settings, "PLATE_DATA_MAX_MB", 1),
            ):
                result = save_plate_data_file(
                    file_name="plate data.pdf",
                    content_type="application/pdf",
                    content=b"plate",
                    uploaded_at=uploaded_at,
                )

            stored_path = Path(result.file_path)

            self.assertTrue(stored_path.is_file())
            self.assertEqual(b"plate", stored_path.read_bytes())
            self.assertEqual("plate data.pdf", result.file_name)
            self.assertEqual("application/pdf", result.content_type)
            self.assertEqual(5, result.file_size)
            self.assertEqual(uploaded_at, result.uploaded_at)
            self.assertEqual(Path(tmpdir) / "plate_data" / "2026" / "01" / "02", stored_path.parent)
            self.assertTrue(stored_path.name.endswith("_plate_data.pdf"))

    def test_save_plate_data_file_rejects_disallowed_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch.object(file_service.settings, "PLATE_DATA_STORAGE_ROOT", tmpdir),
                patch.object(file_service.settings, "PLATE_DATA_ALLOWED_EXT", {".pdf"}),
            ):
                with self.assertRaises(HTTPException) as ctx:
                    save_plate_data_file(
                        file_name="plate.exe",
                        content_type="application/octet-stream",
                        content=b"bad",
                    )

        self.assertEqual(409, ctx.exception.status_code)

    def test_save_plate_data_stream_removes_partial_file_when_size_exceeds_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch.object(file_service.settings, "PLATE_DATA_STORAGE_ROOT", tmpdir),
                patch.object(file_service.settings, "PLATE_DATA_ALLOWED_EXT", {".pdf"}),
                patch.object(file_service.settings, "PLATE_DATA_MAX_MB", 1),
            ):
                with self.assertRaises(HTTPException) as ctx:
                    save_plate_data_stream(
                        file_name="large.pdf",
                        content_type="application/pdf",
                        file_stream=BytesIO(b"x" * ((1024 * 1024) + 1)),
                    )

            stored_files = list((Path(tmpdir) / "plate_data").rglob("*"))

        self.assertEqual(409, ctx.exception.status_code)
        self.assertFalse(any(path.is_file() for path in stored_files))

    def test_get_work_group_plate_data_file_returns_first_instruction_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first_path = Path(tmpdir) / "first.pdf"
            second_path = Path(tmpdir) / "second.pdf"
            first_path.write_bytes(b"first")
            second_path.write_bytes(b"second")

            self._seed_instruction_with_group(
                is_bundle=True,
                file_paths=[str(first_path), str(second_path)],
            )

            result = get_work_group_plate_data_file(self.db, 1)

        self.assertEqual(first_path, result.file_path)
        self.assertEqual("application/pdf", result.media_type)
        self.assertEqual("first.pdf", result.file_name)

    def test_get_work_group_plate_data_file_rejects_non_bundle_group(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "plate.pdf"
            file_path.write_bytes(b"plate")
            self._seed_instruction_with_group(is_bundle=False, file_paths=[str(file_path)])

            with self.assertRaises(HTTPException) as ctx:
                get_work_group_plate_data_file(self.db, 1)

        self.assertEqual(404, ctx.exception.status_code)
        self.assertEqual("Bundle plate data not found", ctx.exception.detail)

    def test_get_inspection_schedule_plate_data_file_returns_instruction_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "plate.pdf"
            file_path.write_bytes(b"plate")

            self._seed_instruction_with_group(is_bundle=True, file_paths=[str(file_path)])
            self._seed_inspection_schedule(outsource_work_group_id=1)

            result = get_inspection_schedule_plate_data_file(self.db, 1)

        self.assertEqual(file_path, result.file_path)
        self.assertEqual("application/pdf", result.media_type)
        self.assertEqual("first.pdf", result.file_name)

    def test_get_inspection_schedule_plate_data_file_rejects_schedule_without_group(self) -> None:
        self._seed_instruction_with_group(is_bundle=True, file_paths=[])
        self._seed_inspection_schedule(outsource_work_group_id=None)

        with self.assertRaises(HTTPException) as ctx:
            get_inspection_schedule_plate_data_file(self.db, 1)

        self.assertEqual(404, ctx.exception.status_code)
        self.assertEqual("Plate data file not found", ctx.exception.detail)

    def _seed_instruction_with_group(
        self,
        *,
        is_bundle: bool,
        file_paths: list[str],
    ) -> None:
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
                instruction_no="OWI260102001",
                instruction_date=date(2026, 1, 2),
                process_type="CUT",
                partner_id=1,
                is_bundle=is_bundle,
            )
        )
        self.db.add(
            OutsourceWorkGroup(
                outsource_work_group_id=1,
                outsource_work_instruction_id=1,
                group_seq="A001",
                process_type="CUT",
                is_bundle=is_bundle,
                sheet_qty=10,
                sheet_cut_count=1,
            )
        )

        for index, file_path in enumerate(file_paths, start=1):
            self.db.add(
                OutsourceWorkInstructionFile(
                    outsource_work_instruction_file_id=index,
                    outsource_work_instruction_id=1,
                    file_name=f"{'first' if index == 1 else 'second'}.pdf",
                    file_path=file_path,
                    content_type="application/pdf",
                )
            )

        self.db.commit()

    def _seed_inspection_schedule(self, *, outsource_work_group_id: int | None) -> None:
        self.db.add(
            Drawing(
                drawing_id=1,
                drawing_no="D-001",
                is_active=True,
            )
        )
        self.db.add(
            RoutingTemplate(
                routing_template_id=1,
                template_code="RT-001",
                template_name="Default",
                is_active=True,
            )
        )
        self.db.add(
            Product(
                product_id=1,
                product_code="P-001",
                product_name="Product",
                uom="EA",
                drawing_id=1,
                routing_template_id=1,
                is_active=True,
            )
        )
        self.db.add(
            OrderLine(
                order_line_id=1,
                order_no="SO-001",
                line_no=1,
                partner_id=1,
                product_id=1,
                order_date=date(2026, 1, 2),
                due_date=date(2026, 1, 10),
                order_qty=10,
                uom="EA",
                status="OPEN",
                is_active=True,
            )
        )
        self.db.add(
            Lot(
                lot_id=1,
                lot_no="LOT-001",
                order_line_id=1,
                product_id=1,
                lot_qty=10,
                uom="EA",
                created_date=date(2026, 1, 2),
                due_date=date(2026, 1, 10),
                status="WAITING",
            )
        )
        self.db.add(
            InspectionSchedule(
                inspection_schedule_id=1,
                lot_id=1,
                outsource_work_group_id=outsource_work_group_id,
                inspection_date=date(2026, 1, 3),
                status="WAITING",
                day_seq=1,
            )
        )
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
