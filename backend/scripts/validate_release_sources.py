from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping
from urllib.parse import urlsplit


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
STATUS_CODE = {"OK": 0, "WARNING": 1, "CRITICAL": 2}
TEXT_SUFFIXES = {
    ".bat",
    ".cmd",
    ".config",
    ".cs",
    ".csproj",
    ".ini",
    ".json",
    ".md",
    ".ps1",
    ".psd1",
    ".props",
    ".py",
    ".sln",
    ".sql",
    ".targets",
    ".toml",
    ".txt",
    ".xaml",
    ".xml",
    ".yaml",
    ".yml",
}
FORBIDDEN_TRACKED_SUFFIXES = {".env", ".key", ".p12", ".pem", ".pfx"}
SECRET_PATTERNS = {
    "private_key": re.compile(
        r"-----BEGIN (?:EC |OPENSSH |RSA )?PRIVATE KEY-----"
    ),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "openai_api_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "postgres_password_url": re.compile(
        r"postgres(?:ql)?(?:\+\w+)?://[^\s/:@]+:[^\s@]+@",
        re.IGNORECASE,
    ),
}


@dataclass(frozen=True)
class ValidationResult:
    name: str
    status: str
    summary: str
    metrics: dict[str, object]


def _run_git(repository_root: Path, *arguments: str) -> str:
    process = subprocess.run(
        ["git", *arguments],
        cwd=repository_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(f"Git command failed: {' '.join(arguments)}")
    return process.stdout


def _tracked_files(repository_root: Path) -> list[Path]:
    output = _run_git(repository_root, "ls-files", "-z")
    return [
        repository_root / relative
        for relative in output.split("\0")
        if relative
    ]


def _forbidden_tracked_files(
    repository_root: Path,
    tracked_files: Iterable[Path],
) -> list[str]:
    forbidden: list[str] = []
    for path in tracked_files:
        relative = path.relative_to(repository_root).as_posix()
        name = path.name.lower()
        suffix = path.suffix.lower()
        if name == ".env" or suffix in FORBIDDEN_TRACKED_SUFFIXES:
            forbidden.append(relative)
    return sorted(forbidden)


def _scan_secret_patterns(
    repository_root: Path,
    tracked_files: Iterable[Path],
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in tracked_files:
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(repository_root).as_posix()
        for pattern_name, pattern in SECRET_PATTERNS.items():
            if (
                pattern_name == "postgres_password_url"
                and relative.startswith("backend/tests/")
            ):
                continue
            if pattern.search(text):
                findings.append(
                    {"path": relative, "pattern": pattern_name}
                )
    return findings


def _sensitive_key_paths(
    value: object,
    prefix: str = "",
) -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if re.search(r"password|secret|token|database.?url", str(key), re.I):
                findings.append(path)
            findings.extend(_sensitive_key_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_sensitive_key_paths(child, f"{prefix}[{index}]"))
    return findings


def _validate_base_url(value: str, *, vendor: bool) -> list[str]:
    errors: list[str] = []
    parsed = urlsplit(value)
    allowed_schemes = {"https"} if vendor else {"http", "https"}
    if parsed.scheme.lower() not in allowed_schemes or not parsed.hostname:
        errors.append("BaseUrl must be an absolute HTTP(S) URL")
        return errors
    if parsed.username or parsed.password:
        errors.append("BaseUrl must not contain credentials")
    if parsed.query or parsed.fragment:
        errors.append("BaseUrl must not contain query or fragment data")
    if parsed.path not in {"", "/"}:
        errors.append("BaseUrl must use the API host root")
    if parsed.hostname.lower() in {"localhost", "127.0.0.1", "::1"}:
        errors.append("Production BaseUrl must not use a loopback host")
    return errors


def validate_wpf_settings(
    path: Path,
    *,
    vendor: bool,
) -> ValidationResult:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return ValidationResult(
            "vendor_wpf_settings" if vendor else "mes_wpf_settings",
            "CRITICAL",
            "Production settings file is missing or invalid JSON",
            {"path": str(path), "error_type": type(exc).__name__},
        )

    errors: list[str] = []
    api = payload.get("Api") if isinstance(payload, dict) else None
    if not isinstance(api, dict):
        errors.append("Api object is required")
        api = {}
    base_url = str(api.get("BaseUrl", "")).strip()
    errors.extend(_validate_base_url(base_url, vendor=vendor))

    normal_timeout = api.get("NormalTimeoutSeconds")
    if not isinstance(normal_timeout, int) or not 1 <= normal_timeout <= 300:
        errors.append("NormalTimeoutSeconds must be between 1 and 300")

    if not vendor:
        bulk_timeout = api.get("BulkTimeoutSeconds")
        file_timeout = api.get("FileTransferTimeoutSeconds")
        if not isinstance(bulk_timeout, int) or not 1 <= bulk_timeout <= 1800:
            errors.append("BulkTimeoutSeconds must be between 1 and 1800")
        if not isinstance(file_timeout, int) or not 1 <= file_timeout <= 3600:
            errors.append("FileTransferTimeoutSeconds must be between 1 and 3600")
        if (
            isinstance(normal_timeout, int)
            and isinstance(bulk_timeout, int)
            and isinstance(file_timeout, int)
            and not normal_timeout <= bulk_timeout <= file_timeout
        ):
            errors.append("Timeouts must satisfy normal <= bulk <= file transfer")

    sensitive_keys = _sensitive_key_paths(payload)
    if sensitive_keys:
        errors.append("Production WPF settings contain sensitive key names")

    name = "vendor_wpf_settings" if vendor else "mes_wpf_settings"
    return ValidationResult(
        name,
        "CRITICAL" if errors else "OK",
        (
            "Production WPF settings are valid"
            if not errors
            else "Production WPF settings require correction"
        ),
        {
            "path": str(path),
            "base_url_host": urlsplit(base_url).hostname if base_url else None,
            "errors": errors,
            "sensitive_key_paths": sensitive_keys,
        },
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_built_outputs(repository_root: Path) -> list[ValidationResult]:
    wpf_root = repository_root / "frontend-wpf" / "Mes.WpfClean" / "Mes.Wpf"
    definitions = (
        ("mes", wpf_root / "Mes.Wpf", "Mes.Wpf.dll"),
        ("vendor", wpf_root / "Mes.Vendor.Wpf", "Mes.Vendor.Wpf.dll"),
    )
    results: list[ValidationResult] = []
    for label, project_root, assembly_name in definitions:
        output_root = project_root / "bin" / "Release" / "net8.0-windows"
        assembly = output_root / assembly_name
        source_settings = project_root / "appsettings.Production.json"
        output_settings = output_root / "appsettings.Production.json"
        errors: list[str] = []
        if not assembly.is_file() or assembly.stat().st_size == 0:
            errors.append("Release assembly is missing or empty")
        if not output_settings.is_file():
            errors.append("Production settings were not copied to Release output")
        elif _sha256(source_settings) != _sha256(output_settings):
            errors.append("Release output settings differ from source settings")
        results.append(
            ValidationResult(
                f"{label}_wpf_release_output",
                "CRITICAL" if errors else "OK",
                (
                    f"{label} WPF Release output is complete"
                    if not errors
                    else f"{label} WPF Release output is incomplete"
                ),
                {
                    "assembly": str(assembly),
                    "settings": str(output_settings),
                    "errors": errors,
                },
            )
        )
    return results


def validate_source(
    repository_root: Path,
    *,
    require_clean_worktree: bool,
) -> list[ValidationResult]:
    tracked_files = _tracked_files(repository_root)
    forbidden_files = _forbidden_tracked_files(repository_root, tracked_files)
    secret_findings = _scan_secret_patterns(repository_root, tracked_files)
    status_output = _run_git(repository_root, "status", "--porcelain")
    dirty_paths = [line[3:] for line in status_output.splitlines() if len(line) >= 4]

    results = [
        ValidationResult(
            "tracked_sensitive_files",
            "CRITICAL" if forbidden_files else "OK",
            (
                "No forbidden credential or private-key files are tracked"
                if not forbidden_files
                else "Forbidden credential or private-key files are tracked"
            ),
            {"paths": forbidden_files},
        ),
        ValidationResult(
            "tracked_secret_patterns",
            "CRITICAL" if secret_findings else "OK",
            (
                "No high-confidence secret pattern was found in tracked source"
                if not secret_findings
                else "A high-confidence secret pattern was found in tracked source"
            ),
            {"findings": secret_findings},
        ),
        ValidationResult(
            "git_worktree",
            (
                "CRITICAL"
                if dirty_paths and require_clean_worktree
                else "WARNING" if dirty_paths else "OK"
            ),
            (
                "Git worktree is clean"
                if not dirty_paths
                else f"Git worktree has {len(dirty_paths)} changed paths"
            ),
            {
                "dirty_path_count": len(dirty_paths),
                "dirty_paths": dirty_paths[:50],
                "clean_required": require_clean_worktree,
            },
        ),
    ]

    wpf_root = repository_root / "frontend-wpf" / "Mes.WpfClean" / "Mes.Wpf"
    results.extend(
        [
            validate_wpf_settings(
                wpf_root / "Mes.Wpf" / "appsettings.Production.json",
                vendor=False,
            ),
            validate_wpf_settings(
                wpf_root / "Mes.Vendor.Wpf" / "appsettings.Production.json",
                vendor=True,
            ),
        ]
    )
    return results


def _build_report(results: list[ValidationResult]) -> dict[str, object]:
    exit_code = max(STATUS_CODE[result.status] for result in results)
    overall_status = next(
        status for status, code in STATUS_CODE.items() if code == exit_code
    )
    return {
        "format_version": 1,
        "overall_status": overall_status,
        "exit_code": exit_code,
        "results": [asdict(result) for result in results],
    }


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _render_text(report: Mapping[str, object]) -> str:
    lines = [f"MES release source validation: {report['overall_status']}"]
    for result in report["results"]:
        lines.append(
            f"[{result['status']}] {result['name']}: {result['summary']}"
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate tracked MES release source and WPF outputs."
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=REPOSITORY_ROOT,
    )
    parser.add_argument(
        "--mode",
        choices=("source", "built-output"),
        default="source",
    )
    parser.add_argument("--require-clean-worktree", action="store_true")
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repository_root = args.repository_root.resolve(strict=True)
    if args.mode == "source":
        results = validate_source(
            repository_root,
            require_clean_worktree=args.require_clean_worktree,
        )
    else:
        results = validate_built_outputs(repository_root)
    report = _build_report(results)
    if args.output_json:
        _write_json_atomic(args.output_json.resolve(), report)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print(_render_text(report))
    return int(report["exit_code"])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(
            f"release_source_validation_failed={type(exc).__name__}",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
