from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_release_sources import (
    _forbidden_tracked_files,
    _scan_secret_patterns,
    validate_wpf_settings,
)


class TrackedFilePolicyTests(unittest.TestCase):
    def test_env_and_private_key_files_are_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            tracked = [root / ".env", root / "certificate.pfx", root / "safe.json"]
            for path in tracked:
                path.write_text("test", encoding="utf-8")

            findings = _forbidden_tracked_files(root, tracked)

        self.assertEqual([".env", "certificate.pfx"], findings)

    def test_high_confidence_secret_is_reported_without_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            source = root / "config.md"
            marker = "-----BEGIN " + "PRIVATE KEY-----"
            source.write_text(
                marker + "\nnot-a-real-key\n",
                encoding="utf-8",
            )

            findings = _scan_secret_patterns(root, [source])

        self.assertEqual(
            [{"path": "config.md", "pattern": "private_key"}],
            findings,
        )

    def test_database_urls_in_tests_do_not_trigger_release_secret_rule(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            test_directory = root / "backend" / "tests"
            test_directory.mkdir(parents=True)
            source = test_directory / "test_url.py"
            source.write_text(
                "URL = 'postgresql://user:fixture-secret@db/test'\n",
                encoding="utf-8",
            )

            findings = _scan_secret_patterns(root, [source])

        self.assertEqual([], findings)


class WpfProductionSettingsTests(unittest.TestCase):
    def _write(self, root: Path, payload: dict) -> Path:
        path = root / "appsettings.Production.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_internal_production_settings_require_ordered_timeouts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            path = self._write(
                Path(temp_directory),
                {
                    "Api": {
                        "BaseUrl": "http://172.30.1.240:8000/",
                        "NormalTimeoutSeconds": 45,
                        "BulkTimeoutSeconds": 150,
                        "FileTransferTimeoutSeconds": 300,
                    }
                },
            )
            result = validate_wpf_settings(path, vendor=False)

        self.assertEqual("OK", result.status)

    def test_vendor_production_settings_require_https(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            path = self._write(
                Path(temp_directory),
                {
                    "Api": {
                        "BaseUrl": "http://vendor.example.com/",
                        "NormalTimeoutSeconds": 45,
                    }
                },
            )
            result = validate_wpf_settings(path, vendor=True)

        self.assertEqual("CRITICAL", result.status)
        self.assertIn("absolute HTTP(S)", result.metrics["errors"][0])

    def test_loopback_and_sensitive_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            path = self._write(
                Path(temp_directory),
                {
                    "Api": {
                        "BaseUrl": "http://127.0.0.1:8000/",
                        "NormalTimeoutSeconds": 45,
                        "BulkTimeoutSeconds": 150,
                        "FileTransferTimeoutSeconds": 300,
                        "Token": "unsafe",
                    }
                },
            )
            result = validate_wpf_settings(path, vendor=False)

        self.assertEqual("CRITICAL", result.status)
        self.assertTrue(result.metrics["sensitive_key_paths"])


if __name__ == "__main__":
    unittest.main()
