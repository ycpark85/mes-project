from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from scripts.check_mes_operations import (
    CheckResult,
    Thresholds,
    _backup_check,
    _build_report,
    _disk_check,
    _load_monitor_database_url,
    _restore_rehearsal_check,
    _status_for_higher_ratio,
    _status_for_lower_ratio,
    _write_history,
)


class ThresholdTests(unittest.TestCase):
    def test_connection_thresholds_are_inclusive(self) -> None:
        self.assertEqual("OK", _status_for_higher_ratio(0.59, 0.60, 0.80))
        self.assertEqual("WARNING", _status_for_higher_ratio(0.60, 0.60, 0.80))
        self.assertEqual("CRITICAL", _status_for_higher_ratio(0.80, 0.60, 0.80))

    def test_disk_thresholds_are_inclusive(self) -> None:
        self.assertEqual("OK", _status_for_lower_ratio(0.21, 0.20, 0.10))
        self.assertEqual("WARNING", _status_for_lower_ratio(0.20, 0.20, 0.10))
        self.assertEqual("CRITICAL", _status_for_lower_ratio(0.10, 0.20, 0.10))


class ConnectionSourceTests(unittest.TestCase):
    def test_monitor_env_file_is_preferred_over_application_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            app_env = root / "app.env"
            monitor_env = root / "monitor.env"
            app_env.write_text(
                "DATABASE_URL=postgresql://app@db/app\n",
                encoding="utf-8",
            )
            monitor_env.write_text(
                "MES_MONITOR_DATABASE_URL=postgresql://monitor@db/app\n",
                encoding="utf-8",
            )
            with patch.dict("os.environ", {}, clear=True):
                value, source = _load_monitor_database_url(app_env, monitor_env)

        self.assertEqual("postgresql://monitor@db/app", value)
        self.assertEqual("monitor_env_file", source)

    def test_process_monitor_url_has_highest_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            app_env = Path(temp_directory) / "app.env"
            app_env.write_text(
                "DATABASE_URL=postgresql://app@db/app\n",
                encoding="utf-8",
            )
            with patch.dict(
                "os.environ",
                {"MES_MONITOR_DATABASE_URL": "postgresql://process@db/app"},
                clear=True,
            ):
                value, source = _load_monitor_database_url(app_env, None)

        self.assertEqual("postgresql://process@db/app", value)
        self.assertEqual("process_environment", source)


class BackupAgeTests(unittest.TestCase):
    def _write_manifest(self, backup_directory: Path, created_at: datetime) -> None:
        backup_directory.mkdir()
        (backup_directory / "database.dump").write_bytes(b"dump")
        (backup_directory / "manifest.json").write_text(
            json.dumps(
                {
                    "format_version": 1,
                    "backup_id": backup_directory.name,
                    "created_at_utc": created_at.isoformat(),
                    "consistency_mode": "maintenance",
                    "database": {
                        "name": "mes",
                        "dump_file": "database.dump",
                        "dump_bytes": 4,
                        "dump_sha256": "unused-in-age-check",
                    },
                    "storage_sets": [],
                }
            ),
            encoding="utf-8",
        )

    def test_latest_valid_backup_controls_age_status(self) -> None:
        now = datetime(2026, 7, 14, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            self._write_manifest(root / "old", now - timedelta(hours=70))
            self._write_manifest(root / "latest", now - timedelta(hours=27))
            result = _backup_check(root, now, Thresholds())

        self.assertEqual("WARNING", result.status)
        self.assertEqual("latest", result.metrics["backup_id"])

    def test_missing_completed_backup_is_critical(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            result = _backup_check(
                Path(temp_directory),
                datetime.now(UTC),
                Thresholds(),
            )

        self.assertEqual("CRITICAL", result.status)

    def test_missing_backup_root_is_critical_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            missing = Path(temp_directory) / "missing"
            result = _backup_check(
                missing,
                datetime.now(UTC),
                Thresholds(),
            )

        self.assertEqual("CRITICAL", result.status)

    def test_backup_with_missing_dump_is_not_treated_as_completed(self) -> None:
        now = datetime(2026, 7, 14, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            backup = root / "broken"
            self._write_manifest(backup, now - timedelta(hours=1))
            (backup / "database.dump").unlink()
            result = _backup_check(root, now, Thresholds())

        self.assertEqual("CRITICAL", result.status)


class RestoreRehearsalTests(unittest.TestCase):
    def test_old_restore_record_is_warning(self) -> None:
        now = datetime(2026, 7, 14, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as temp_directory:
            record = Path(temp_directory) / "restore.json"
            record.write_text(
                json.dumps(
                    {
                        "verified_at_utc": (now - timedelta(days=95)).isoformat(),
                        "backup_id": "mes_20260410T000000Z",
                    }
                ),
                encoding="utf-8",
            )
            result = _restore_rehearsal_check(record, now, Thresholds())

        self.assertEqual("WARNING", result.status)

    def test_invalid_restore_record_is_critical(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            record = Path(temp_directory) / "restore.json"
            record.write_text("{}", encoding="utf-8")
            result = _restore_rehearsal_check(
                record,
                datetime.now(UTC),
                Thresholds(),
            )

        self.assertEqual("CRITICAL", result.status)


class ReportAndHistoryTests(unittest.TestCase):
    def test_highest_check_status_controls_exit_code(self) -> None:
        report = _build_report(
            [
                CheckResult("one", "OK", "ok", {}),
                CheckResult("two", "WARNING", "warning", {}),
            ],
            datetime(2026, 7, 14, tzinfo=UTC),
        )

        self.assertEqual("WARNING", report["overall_status"])
        self.assertEqual(1, report["exit_code"])

    def test_history_write_is_atomic_and_does_not_overwrite(self) -> None:
        report = _build_report(
            [CheckResult("one", "OK", "ok", {})],
            datetime(2026, 7, 14, 1, 2, 3, tzinfo=UTC),
        )
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            output = _write_history(root, report)
            payload = json.loads(output.read_text(encoding="utf-8"))
            with self.assertRaises(FileExistsError):
                _write_history(root, report)

        self.assertEqual("OK", payload["overall_status"])

    def test_unavailable_disk_path_is_critical(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            missing = Path(temp_directory) / "missing"
            result = _disk_check([missing], Thresholds())

        self.assertEqual("CRITICAL", result.status)


if __name__ == "__main__":
    unittest.main()
