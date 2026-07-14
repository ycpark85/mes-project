from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.api.v1 import (
    drawing_revisions,
    inspection_results,
    inspection_schedules,
    outsource_work_instructions,
)


class FileResponseDbReleaseTests(unittest.TestCase):
    def test_drawing_download_closes_session_before_response(self) -> None:
        db = MagicMock()
        revision_file = SimpleNamespace(
            file_uri="stored/file.pdf",
            content_type="application/pdf",
            original_filename="drawing.pdf",
        )
        db.query.return_value.filter.return_value.first.return_value = revision_file

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "drawing.pdf"
            file_path.write_bytes(b"drawing")
            with patch.object(
                drawing_revisions,
                "_abs_path_from_uri",
                return_value=file_path,
            ):
                response = drawing_revisions.download_revision_file(1, db)

        self.assertEqual(str(file_path), response.path)
        db.close.assert_called_once_with()

    def test_inspection_attachment_download_closes_session(self) -> None:
        db = MagicMock()
        result = SimpleNamespace(
            file_path=Path("attachment.jpg"),
            media_type="image/jpeg",
            file_name="attachment.jpg",
        )

        with patch.object(
            inspection_results,
            "get_defect_attachment_download",
            return_value=result,
        ):
            inspection_results.get_result_attachment_content(1, db, object())

        db.close.assert_called_once_with()

    def test_inspection_plate_download_closes_session(self) -> None:
        db = MagicMock()
        result = SimpleNamespace(
            file_path=Path("plate.pdf"),
            media_type="application/pdf",
            file_name="plate.pdf",
        )

        with patch.object(
            inspection_schedules,
            "get_inspection_schedule_plate_data_file",
            return_value=result,
        ):
            inspection_schedules.download_inspection_schedule_plate_data(1, db)

        db.close.assert_called_once_with()

    def test_purchase_order_excel_download_closes_session(self) -> None:
        db = MagicMock()
        result = SimpleNamespace(
            file_bytes=b"excel",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="purchase-order.xlsx",
        )

        with patch.object(
            outsource_work_instructions,
            "build_purchase_order_excel_download",
            return_value=result,
        ):
            outsource_work_instructions.download_outsource_purchase_order_excel(1, db)

        db.close.assert_called_once_with()

    def test_work_group_plate_download_closes_session(self) -> None:
        db = MagicMock()
        result = SimpleNamespace(
            file_path=Path("plate.pdf"),
            media_type="application/pdf",
            file_name="plate.pdf",
        )

        with patch.object(
            outsource_work_instructions,
            "get_work_group_plate_data_file",
            return_value=result,
        ):
            outsource_work_instructions.download_work_group_plate_data(1, db)

        db.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
