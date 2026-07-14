from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from app.core.config import Settings
from app.core.db import build_engine_kwargs, set_local_statement_timeout


class DatabaseRuntimeSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(database_url="postgresql+psycopg://mes@localhost/mes")

    def test_postgresql_engine_kwargs_include_pool_and_server_timeouts(self) -> None:
        kwargs = build_engine_kwargs(self.settings.database_url, self.settings)

        self.assertTrue(kwargs["pool_pre_ping"])
        self.assertEqual(5, kwargs["pool_size"])
        self.assertEqual(5, kwargs["max_overflow"])
        self.assertEqual(10, kwargs["pool_timeout"])
        self.assertEqual(1800, kwargs["pool_recycle"])
        self.assertEqual(5, kwargs["connect_args"]["connect_timeout"])
        self.assertEqual("mes-api", kwargs["connect_args"]["application_name"])
        self.assertIn("statement_timeout=30000", kwargs["connect_args"]["options"])
        self.assertIn("lock_timeout=5000", kwargs["connect_args"]["options"])
        self.assertIn(
            "idle_in_transaction_session_timeout=60000",
            kwargs["connect_args"]["options"],
        )

    def test_non_postgresql_engine_does_not_receive_queue_pool_options(self) -> None:
        kwargs = build_engine_kwargs("sqlite:///:memory:", self.settings)

        self.assertEqual({"pool_pre_ping": True}, kwargs)

    def test_bulk_timeout_is_set_for_current_postgresql_transaction(self) -> None:
        db = MagicMock()
        db.get_bind.return_value.dialect.name = "postgresql"

        set_local_statement_timeout(db, timeout_seconds=120)

        statement, parameters = db.execute.call_args.args
        self.assertIn("set_config", str(statement))
        self.assertEqual({"timeout": "120000ms"}, parameters)

    def test_bulk_timeout_is_skipped_for_sqlite(self) -> None:
        db = MagicMock()
        db.get_bind.return_value.dialect.name = "sqlite"

        set_local_statement_timeout(db, timeout_seconds=120)

        db.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
