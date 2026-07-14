from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import re
import sys
from pathlib import Path


REQUIRED_IMPORTS = (
    "alembic",
    "fastapi",
    "openpyxl",
    "psycopg",
    "pydantic",
    "sqlalchemy",
    "uvicorn",
)


def canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def parse_requirements(path: Path) -> dict[str, tuple[str, str]]:
    expected: dict[str, tuple[str, str]] = {}
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8-sig")
    for line_number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s;]+)", value)
        if not match:
            raise ValueError(f"requirement_line_not_pinned={line_number}")
        display_name, version = match.groups()
        normalized = canonical_name(display_name)
        if normalized in expected:
            raise ValueError(f"duplicate_requirement={display_name}")
        expected[normalized] = (display_name, version)
    if not expected:
        raise ValueError("requirements_empty")
    return expected


def verify_runtime(requirements_path: Path) -> dict[str, object]:
    expected = parse_requirements(requirements_path)
    installed = {
        canonical_name(distribution.metadata["Name"]): distribution.version
        for distribution in importlib.metadata.distributions()
        if distribution.metadata.get("Name")
    }
    missing: list[str] = []
    mismatches: list[dict[str, str]] = []
    for normalized, (display_name, expected_version) in expected.items():
        actual_version = installed.get(normalized)
        if actual_version is None:
            missing.append(display_name)
        elif actual_version != expected_version:
            mismatches.append(
                {
                    "package": display_name,
                    "expected": expected_version,
                    "actual": actual_version,
                }
            )
    import_failures: list[dict[str, str]] = []
    for module_name in REQUIRED_IMPORTS:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            import_failures.append(
                {"module": module_name, "error_type": type(exc).__name__}
            )
    status = "OK" if not missing and not mismatches and not import_failures else "CRITICAL"
    return {
        "format_version": 1,
        "status": status,
        "python_version": ".".join(str(part) for part in sys.version_info[:3]),
        "requirement_count": len(expected),
        "missing": sorted(missing),
        "version_mismatches": mismatches,
        "import_failures": import_failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the installed MES Python runtime.")
    parser.add_argument("--requirements", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = verify_runtime(args.requirements.resolve(strict=True))
    except Exception as exc:
        print(
            json.dumps(
                {"status": "CRITICAL", "error_type": type(exc).__name__},
                ensure_ascii=True,
            )
        )
        return 2
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["status"] == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
