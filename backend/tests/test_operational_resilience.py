import json
import re
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, TimeoutError as SQLAlchemyTimeoutError
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api.v1.endpoints.health import readiness
from app.core.db import get_db
from app.core.observability import (
    REQUEST_ID_HEADER,
    database_operational_error_handler,
    database_pool_timeout_handler,
    observe_request,
    register_slow_query_logging,
)


class _PostgresError(Exception):
    def __init__(self, sqlstate: str):
        super().__init__("database error")
        self.sqlstate = sqlstate


def _request(
    path: str,
    *,
    request_id: str | None = None,
) -> Request:
    headers = []
    if request_id is not None:
        headers.append((b"x-request-id", request_id.encode("ascii")))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"ignored=sensitive",
            "headers": headers,
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
    )


class RequestObservabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_request_id_is_returned_and_route_template_is_logged(self) -> None:
        request = _request("/items/42", request_id="desktop-123")

        async def call_next(current_request: Request):
            current_request.scope["route"] = SimpleNamespace(path="/items/{item_id}")
            return JSONResponse({"item_id": 42})

        with self.assertLogs("mes.request", level="INFO") as captured:
            response = await observe_request(
                request,
                call_next,
                slow_request_threshold_ms=60_000,
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("desktop-123", response.headers[REQUEST_ID_HEADER])
        log_output = "\n".join(captured.output)
        self.assertIn("path=/items/{item_id}", log_output)
        self.assertNotIn("ignored=sensitive", log_output)

    async def test_invalid_request_id_is_replaced(self) -> None:
        request = _request("/items/1", request_id="invalid request id with spaces")

        async def call_next(current_request: Request):
            return JSONResponse({"item_id": 1})

        response = await observe_request(
            request,
            call_next,
            slow_request_threshold_ms=60_000,
        )

        request_id = response.headers[REQUEST_ID_HEADER]
        self.assertRegex(request_id, re.compile(r"^[0-9a-f]{32}$"))

    async def test_failed_request_log_excludes_exception_message(self) -> None:
        request = _request("/fault/unexpected", request_id="request-0")

        async def call_next(current_request: Request):
            raise ValueError("must-not-be-logged")

        with self.assertLogs("mes.request", level="ERROR") as captured:
            with self.assertRaises(ValueError):
                await observe_request(
                    request,
                    call_next,
                    slow_request_threshold_ms=60_000,
                )

        log_output = "\n".join(captured.output)
        self.assertIn("error_type=ValueError", log_output)
        self.assertNotIn("must-not-be-logged", log_output)

    async def test_pool_timeout_returns_503_without_internal_details(self) -> None:
        request = _request("/fault/pool")
        request.state.request_id = "request-1"
        response = await database_pool_timeout_handler(
            request,
            SQLAlchemyTimeoutError("pool exhausted"),
        )

        self.assertEqual(503, response.status_code)
        body = json.loads(response.body)
        self.assertIn("데이터베이스가 사용 중", body["detail"])
        self.assertNotIn("pool exhausted", response.body.decode())
        self.assertEqual(body["request_id"], response.headers[REQUEST_ID_HEADER])

    async def test_query_timeout_returns_504_without_sql_or_parameters(self) -> None:
        request = _request("/fault/query-timeout")
        request.state.request_id = "request-2"
        response = await database_operational_error_handler(
            request,
            OperationalError(
                "SELECT sensitive_value",
                {"secret": "must-not-be-logged"},
                _PostgresError("57014"),
            ),
        )

        self.assertEqual(504, response.status_code)
        response_text = response.body.decode()
        self.assertNotIn("sensitive_value", response_text)
        self.assertNotIn("must-not-be-logged", response_text)

    async def test_database_connection_error_returns_503(self) -> None:
        request = _request("/fault/database")
        request.state.request_id = "request-3"
        response = await database_operational_error_handler(
            request,
            OperationalError(
                "SELECT sensitive_value",
                {"secret": "must-not-be-logged"},
                _PostgresError("08006"),
            ),
        )

        self.assertEqual(503, response.status_code)
        self.assertIn("데이터베이스에 연결할 수 없습니다", json.loads(response.body)["detail"])


class ReadinessTests(unittest.TestCase):
    @patch("app.api.v1.endpoints.health.engine.connect")
    def test_readiness_executes_database_probe(self, connect: MagicMock) -> None:
        connection = connect.return_value.__enter__.return_value

        result = readiness()

        self.assertEqual({"status": "ready"}, result)
        connection.execute.assert_called_once()

    @patch("app.api.v1.endpoints.health.engine.connect")
    def test_readiness_returns_503_when_database_is_unavailable(
        self,
        connect: MagicMock,
    ) -> None:
        connect.side_effect = OperationalError(
            "SELECT 1",
            {},
            _PostgresError("08006"),
        )

        result = readiness()

        self.assertEqual(503, result.status_code)
        self.assertEqual({"status": "unavailable"}, json.loads(result.body))


class DatabaseSessionTests(unittest.TestCase):
    @patch("app.core.db.SessionLocal")
    def test_get_db_rolls_back_active_transaction_on_error(
        self,
        session_factory: MagicMock,
    ) -> None:
        session = session_factory.return_value
        session.in_transaction.return_value = True
        dependency = get_db()
        self.assertIs(session, next(dependency))

        with self.assertRaisesRegex(RuntimeError, "failed request"):
            dependency.throw(RuntimeError("failed request"))

        session.rollback.assert_called_once_with()
        session.close.assert_called_once_with()


class SlowQueryLoggingTests(unittest.TestCase):
    def test_slow_query_log_excludes_sql_and_parameters(self) -> None:
        engine = create_engine("sqlite://")
        register_slow_query_logging(engine, slow_query_threshold_ms=0)

        with self.assertLogs("mes.database", level="WARNING") as captured:
            with engine.connect() as connection:
                connection.execute(
                    text("SELECT :secret"),
                    {"secret": "must-not-be-logged"},
                )

        log_output = "\n".join(captured.output)
        self.assertIn("statement_type=SELECT", log_output)
        self.assertNotIn("SELECT :secret", log_output)
        self.assertNotIn("must-not-be-logged", log_output)
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
