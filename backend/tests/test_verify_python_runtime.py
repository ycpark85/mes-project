from __future__ import annotations

import importlib.metadata
import tempfile
import unittest
from pathlib import Path

from scripts.verify_python_runtime import canonical_name, parse_requirements, verify_runtime


class PythonRuntimeVerificationTests(unittest.TestCase):
    def test_requirement_names_are_canonicalized(self) -> None:
        self.assertEqual("psycopg-binary", canonical_name("psycopg_binary"))
        self.assertEqual("pydantic-settings", canonical_name("Pydantic.Settings"))

    def test_unpinned_requirement_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            path = Path(temp_directory) / "requirements.txt"
            path.write_text("fastapi>=1\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "not_pinned"):
                parse_requirements(path)

    def test_current_runtime_matches_a_pinned_installed_distribution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            path = Path(temp_directory) / "requirements.txt"
            pip_version = importlib.metadata.version("pip")
            path.write_text(f"pip=={pip_version}\n", encoding="utf-8")

            report = verify_runtime(path)

        self.assertEqual("OK", report["status"])
        self.assertEqual([], report["missing"])
        self.assertEqual([], report["version_mismatches"])
