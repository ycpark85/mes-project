from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.mes_backup_common import (
    ADMIN_DATABASE_URL_ENV_KEY,
    collect_storage_roots,
    copy_storage_root,
    ensure_backup_path_is_separate,
    load_runtime_values,
    parse_postgres_url,
    safe_child_path,
    validate_restore_database_name,
    verify_file_records,
)
from scripts.verify_mes_restore import _write_restore_record


class PostgresUrlTests(unittest.TestCase):
    def test_admin_database_url_can_be_injected_without_writing_it_to_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            env_file = Path(temp_directory) / ".env"
            env_file.write_text("DATABASE_URL=postgresql://app@db/mes\n", encoding="utf-8")
            with patch.dict(
                "os.environ",
                {ADMIN_DATABASE_URL_ENV_KEY: "postgresql://admin@db/postgres"},
            ):
                values = load_runtime_values(env_file)

        self.assertEqual(
            "postgresql://admin@db/postgres",
            values[ADMIN_DATABASE_URL_ENV_KEY],
        )

    def test_driver_url_and_encoded_credentials_are_parsed_without_exposure(self) -> None:
        connection = parse_postgres_url(
            "postgresql+psycopg://mes_user:p%40ss%3Aword@db.local:5544/mes_db?sslmode=require"
        )

        self.assertEqual("db.local", connection.host)
        self.assertEqual(5544, connection.port)
        self.assertEqual("mes_user", connection.username)
        self.assertEqual("p@ss:word", connection.password)
        self.assertEqual("mes_db", connection.database)
        self.assertEqual("require", connection.sslmode)
        self.assertNotIn("p@ss:word", connection.tool_args())
        self.assertEqual("p@ss:word", connection.child_environment()["PGPASSWORD"])

    def test_non_postgres_url_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "PostgreSQL"):
            parse_postgres_url("sqlite:///mes.db")

    def test_unsupported_connection_option_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            parse_postgres_url(
                "postgresql://mes_user:secret@db.local/mes_db?application_name=unsafe"
            )


class StorageBackupTests(unittest.TestCase):
    def test_duplicate_configured_storage_roots_are_copied_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            storage = Path(temp_directory) / "storage"
            storage.mkdir()
            roots = collect_storage_roots(
                {
                    "DRAWING_STORAGE_ROOT": str(storage),
                    "DEFECT_PHOTO_STORAGE_ROOT": str(storage),
                    "PLATE_DATA_STORAGE_ROOT": str(storage),
                }
            )

        self.assertEqual(1, len(roots))
        self.assertEqual(
            {
                "DRAWING_STORAGE_ROOT",
                "DEFECT_PHOTO_STORAGE_ROOT",
                "PLATE_DATA_STORAGE_ROOT",
            },
            set(roots[0]["labels"]),
        )

    def test_explicit_storage_roots_can_be_used_when_env_paths_are_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            roots = collect_storage_roots(
                {"CLI_STORAGE_ROOT_1": temp_directory},
                ("CLI_STORAGE_ROOT_1",),
            )

        self.assertEqual(1, len(roots))
        self.assertEqual(["CLI_STORAGE_ROOT_1"], roots[0]["labels"])

    def test_backup_root_cannot_overlap_storage_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            storage = root / "storage"
            storage.mkdir()

            with self.assertRaisesRegex(ValueError, "must not contain"):
                ensure_backup_path_is_separate(storage / "backups", [storage])

            with self.assertRaisesRegex(ValueError, "must not contain"):
                ensure_backup_path_is_separate(root, [storage])

    def test_copy_and_verify_detects_file_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            source = root / "source"
            destination = root / "backup"
            source.mkdir()
            (source / "nested").mkdir()
            (source / "nested" / "sample.txt").write_text(
                "MES backup test",
                encoding="utf-8",
            )

            result = copy_storage_root(source, destination)
            verify_file_records(destination, result["files"])
            (destination / "nested" / "sample.txt").write_text(
                "corrupted",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "mismatch"):
                verify_file_records(destination, result["files"])

    def test_linked_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            source = root / "source"
            destination = root / "backup"
            source.mkdir()
            target = root / "target.txt"
            target.write_text("target", encoding="utf-8")
            link = source / "link.txt"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("Symbolic links are not available for this test user")

            with self.assertRaisesRegex(ValueError, "linked files"):
                copy_storage_root(source, destination)


class RestoreSafetyTests(unittest.TestCase):
    def test_only_generated_restore_database_names_are_allowed(self) -> None:
        validate_restore_database_name("mes_restore_test_20260714_120000", "mes")

        for unsafe_name in ("mes", "production", "mes_restore_test_ABC", "other_test"):
            with self.subTest(unsafe_name=unsafe_name):
                with self.assertRaises(ValueError):
                    validate_restore_database_name(unsafe_name, "mes")

    def test_manifest_path_cannot_escape_backup_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                safe_child_path(root, "../database.dump")

    def test_restore_success_record_is_written_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            record = Path(temp_directory) / "restore-record.json"
            _write_restore_record(
                record,
                backup_id="mes_20260714T012236Z",
                target_database="mes_restore_test_20260714_012803",
                database_snapshot={
                    "alembic_version": "29d3e4f5a6b7",
                    "public_table_count": 51,
                },
                storage_set_count=1,
            )
            payload = json.loads(record.read_text(encoding="utf-8"))

        self.assertEqual("mes_20260714T012236Z", payload["backup_id"])
        self.assertTrue(payload["restored_artifacts_removed"])


if __name__ == "__main__":
    unittest.main()
