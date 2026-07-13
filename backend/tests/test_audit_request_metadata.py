from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from sqlalchemy import Text
from starlette.requests import Request

from app.api.v1.auth import _write_auth_audit_log
from app.api.v1.vendor_portal import _write_vendor_audit_log
from app.models.auth_audit_log import AuthAuditLog
from app.models.vendor_portal_audit_log import VendorPortalAuditLog
from app.services.audit_request_metadata import (
    MAX_USER_AGENT_LENGTH,
    normalize_user_agent,
)


class AuditRequestMetadataTests(unittest.TestCase):
    def test_normalize_user_agent_handles_empty_control_and_oversized_values(self) -> None:
        self.assertEqual((None, False), self._as_tuple(normalize_user_agent(None)))

        cleaned = normalize_user_agent(" MES\tClient\n1.0 ")
        self.assertEqual("MES Client 1.0", cleaned.value)
        self.assertFalse(cleaned.truncated)

        oversized = normalize_user_agent("A" * (MAX_USER_AGENT_LENGTH + 100))
        self.assertEqual(MAX_USER_AGENT_LENGTH, len(oversized.value or ""))
        self.assertTrue(oversized.truncated)

    def test_auth_audit_writer_uses_common_user_agent_policy(self) -> None:
        db = Mock()
        request = self._request_with_user_agent("A" * (MAX_USER_AGENT_LENGTH + 1))

        _write_auth_audit_log(
            db,
            event_type="LOGIN_FAILED",
            request=request,
            login_id="tester",
            user_id=None,
            success=False,
            reason="invalid_credentials",
        )

        log = db.add.call_args.args[0]
        self.assertIsInstance(log, AuthAuditLog)
        self.assertEqual(MAX_USER_AGENT_LENGTH, len(log.user_agent or ""))
        self.assertTrue(log.user_agent_truncated)
        self.assertEqual("127.0.0.1", log.client_ip)

    def test_vendor_audit_writer_uses_common_user_agent_policy(self) -> None:
        db = Mock()
        request = self._request_with_user_agent("Vendor\tClient")
        context = SimpleNamespace(
            user=SimpleNamespace(user_id=10),
            partner_id=20,
        )

        _write_vendor_audit_log(
            db,
            request=request,
            context=context,
            action_type="WORK_DONE",
            outsource_work_group_id=30,
            before_status="VENDOR_RECEIVED",
            after_status="WORK_DONE",
            remark=None,
        )

        log = db.add.call_args.args[0]
        self.assertIsInstance(log, VendorPortalAuditLog)
        self.assertEqual("Vendor Client", log.user_agent)
        self.assertFalse(log.user_agent_truncated)
        self.assertEqual("127.0.0.1", log.request_ip)

    def test_audit_models_use_text_and_truncation_flag(self) -> None:
        for model in (AuthAuditLog, VendorPortalAuditLog):
            with self.subTest(model=model.__name__):
                self.assertIsInstance(model.__table__.c.user_agent.type, Text)
                self.assertFalse(model.__table__.c.user_agent_truncated.nullable)

    @staticmethod
    def _request_with_user_agent(user_agent: str) -> Request:
        return Request(
            {
                "type": "http",
                "headers": [(b"user-agent", user_agent.encode("utf-8"))],
                "client": ("127.0.0.1", 12345),
                "method": "POST",
                "path": "/",
                "scheme": "http",
                "server": ("testserver", 80),
                "query_string": b"",
            }
        )

    @staticmethod
    def _as_tuple(value) -> tuple[str | None, bool]:
        return value.value, value.truncated


if __name__ == "__main__":
    unittest.main()
