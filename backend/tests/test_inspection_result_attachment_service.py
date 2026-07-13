from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app.models.inspection_defect_attachment import InspectionDefectAttachment
from app.models.inspection_schedule import InspectionSchedule
from app.services import inspection_result_attachment_service as attachment_service
from app.services.inspection_result_attachment_service import (
    get_defect_attachment_download,
    save_defect_photo_upload,
)


class FakeDb:
    def __init__(self):
        self.rows = {}

    def add_row(self, model, row_id: int, row):
        self.rows[(model, row_id)] = row

    def get(self, model, row_id: int):
        return self.rows.get((model, row_id))


class InspectionResultAttachmentServiceTests(unittest.TestCase):
    def test_save_defect_photo_upload_writes_file_under_schedule_folder(self) -> None:
        db = FakeDb()
        db.add_row(InspectionSchedule, 1, object())

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch.object(attachment_service.settings, "DEFECT_PHOTO_STORAGE_ROOT", tmpdir),
                patch.object(attachment_service.settings, "DEFECT_PHOTO_ALLOWED_EXT", {".jpg"}),
                patch.object(attachment_service.settings, "DEFECT_PHOTO_MAX_MB", 1),
            ):
                result = save_defect_photo_upload(
                    db,
                    1,
                    file_name="bad name.jpg",
                    content_type="image/jpeg",
                    file_stream=BytesIO(b"photo"),
                )

            stored_path = Path(tmpdir) / result.file_uri

            self.assertTrue(stored_path.is_file())
            self.assertEqual(b"photo", stored_path.read_bytes())
            self.assertEqual("bad_name.jpg", result.file_name)
            self.assertEqual("image/jpeg", result.mime_type)
            self.assertEqual(5, result.file_size)
            self.assertEqual(Path(tmpdir) / "defect_photos" / "1", stored_path.parent)

    def test_save_defect_photo_upload_rejects_missing_schedule(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            save_defect_photo_upload(
                FakeDb(),
                999,
                file_name="photo.jpg",
                content_type="image/jpeg",
                file_stream=BytesIO(b"photo"),
            )

        self.assertEqual(404, ctx.exception.status_code)

    def test_save_defect_photo_upload_rejects_disallowed_extension(self) -> None:
        db = FakeDb()
        db.add_row(InspectionSchedule, 1, object())

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch.object(attachment_service.settings, "DEFECT_PHOTO_STORAGE_ROOT", tmpdir),
                patch.object(attachment_service.settings, "DEFECT_PHOTO_ALLOWED_EXT", {".jpg"}),
            ):
                with self.assertRaises(HTTPException) as ctx:
                    save_defect_photo_upload(
                        db,
                        1,
                        file_name="photo.exe",
                        content_type="application/octet-stream",
                        file_stream=BytesIO(b"bad"),
                    )

        self.assertEqual(400, ctx.exception.status_code)

    def test_save_defect_photo_upload_rejects_empty_file(self) -> None:
        db = FakeDb()
        db.add_row(InspectionSchedule, 1, object())

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch.object(attachment_service.settings, "DEFECT_PHOTO_STORAGE_ROOT", tmpdir),
                patch.object(attachment_service.settings, "DEFECT_PHOTO_ALLOWED_EXT", {".jpg"}),
                patch.object(attachment_service.settings, "DEFECT_PHOTO_MAX_MB", 1),
            ):
                with self.assertRaises(HTTPException) as ctx:
                    save_defect_photo_upload(
                        db,
                        1,
                        file_name="photo.jpg",
                        content_type="image/jpeg",
                        file_stream=BytesIO(b""),
                    )

        self.assertEqual(400, ctx.exception.status_code)

    def test_get_defect_attachment_download_returns_file_metadata(self) -> None:
        db = FakeDb()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "defect_photos" / "1" / "photo.png"
            file_path.parent.mkdir(parents=True)
            file_path.write_bytes(b"png")

            db.add_row(
                InspectionDefectAttachment,
                10,
                InspectionDefectAttachment(
                    inspection_defect_attachment_id=10,
                    inspection_defect_id=1,
                    file_uri="defect_photos/1/photo.png",
                    file_name="photo.png",
                    mime_type=None,
                ),
            )

            with patch.object(attachment_service.settings, "DEFECT_PHOTO_STORAGE_ROOT", tmpdir):
                result = get_defect_attachment_download(db, 10)

        self.assertEqual(file_path, result.file_path)
        self.assertEqual("image/png", result.media_type)
        self.assertEqual("photo.png", result.file_name)

    def test_get_defect_attachment_download_rejects_path_traversal(self) -> None:
        db = FakeDb()
        db.add_row(
            InspectionDefectAttachment,
            10,
            InspectionDefectAttachment(
                inspection_defect_attachment_id=10,
                inspection_defect_id=1,
                file_uri="../outside.png",
                file_name="outside.png",
                mime_type="image/png",
            ),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(attachment_service.settings, "DEFECT_PHOTO_STORAGE_ROOT", tmpdir):
                with self.assertRaises(HTTPException) as ctx:
                    get_defect_attachment_download(db, 10)

        self.assertEqual(400, ctx.exception.status_code)


if __name__ == "__main__":
    unittest.main()
