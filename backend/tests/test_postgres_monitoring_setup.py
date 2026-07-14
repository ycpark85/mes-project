from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.configure_postgres_monitoring import (
    _load_monitor_url,
    _preload_items,
    _validate_connections,
    _with_pg_stat_statements,
    build_scram_verifier,
)
from scripts.mes_backup_common import parse_postgres_url


class PreloadSettingTests(unittest.TestCase):
    def test_pg_stat_statements_is_appended_without_losing_existing_libraries(self) -> None:
        value, changed = _with_pg_stat_statements("auto_explain")

        self.assertTrue(changed)
        self.assertEqual(["auto_explain", "pg_stat_statements"], _preload_items(value))

    def test_existing_pg_stat_statements_is_not_duplicated(self) -> None:
        value, changed = _with_pg_stat_statements(
            " auto_explain, pg_stat_statements "
        )

        self.assertFalse(changed)
        self.assertEqual(["auto_explain", "pg_stat_statements"], _preload_items(value))


class ScramVerifierTests(unittest.TestCase):
    def test_verifier_contains_no_plaintext_password(self) -> None:
        verifier = build_scram_verifier(
            "monitor-secret",
            salt=b"0123456789abcdef",
        )

        self.assertTrue(verifier.startswith("SCRAM-SHA-256$4096:"))
        self.assertNotIn("monitor-secret", verifier)
        parts = verifier.split("$")
        self.assertEqual(3, len(parts))
        salt_part = parts[1].split(":", 1)[1]
        stored_key, server_key = parts[2].split(":", 1)
        self.assertEqual(b"0123456789abcdef", base64.b64decode(salt_part))
        self.assertEqual(32, len(base64.b64decode(stored_key)))
        self.assertEqual(32, len(base64.b64decode(server_key)))

    def test_non_ascii_monitor_password_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "printable ASCII"):
            build_scram_verifier("비밀번호")


class MonitoringConnectionTests(unittest.TestCase):
    def test_monitor_env_file_can_use_database_url_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            monitor_env = Path(temp_directory) / "monitor.env"
            monitor_env.write_text(
                "DATABASE_URL=postgresql://mes_monitor@db/mes\n",
                encoding="utf-8",
            )
            with patch.dict("os.environ", {}, clear=True):
                value = _load_monitor_url(monitor_env)

        self.assertEqual("postgresql://mes_monitor@db/mes", value)

    def test_monitor_must_use_same_server_and_database(self) -> None:
        app = parse_postgres_url("postgresql://mes_app@db:5432/mes")
        admin = parse_postgres_url("postgresql://admin@db:5432/postgres")
        wrong_server = parse_postgres_url(
            "postgresql://mes_monitor:secret@other:5432/mes"
        )
        wrong_database = parse_postgres_url(
            "postgresql://mes_monitor:secret@db:5432/other"
        )

        with self.assertRaisesRegex(ValueError, "same PostgreSQL server"):
            _validate_connections(app, admin, wrong_server)
        with self.assertRaisesRegex(ValueError, "application database"):
            _validate_connections(app, admin, wrong_database)

    def test_monitor_role_cannot_reuse_application_role(self) -> None:
        app = parse_postgres_url("postgresql://mes_monitor@db/mes")
        admin = parse_postgres_url("postgresql://admin@db/postgres")
        monitor = parse_postgres_url(
            "postgresql://mes_monitor:secret@db/mes"
        )

        with self.assertRaisesRegex(ValueError, "separate"):
            _validate_connections(app, admin, monitor)

    def test_unrelated_role_name_is_rejected(self) -> None:
        app = parse_postgres_url("postgresql://mes_app@db/mes")
        admin = parse_postgres_url("postgresql://admin@db/postgres")
        monitor = parse_postgres_url(
            "postgresql://ordinary_user:secret@db/mes"
        )

        with self.assertRaisesRegex(ValueError, "mes_monitor"):
            _validate_connections(app, admin, monitor)


if __name__ == "__main__":
    unittest.main()
