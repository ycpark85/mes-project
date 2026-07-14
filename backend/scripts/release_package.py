from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping

from scripts.validate_release_sources import (
    SECRET_PATTERNS,
    TEXT_SUFFIXES,
    _sensitive_key_paths,
    _validate_base_url,
)


MANIFEST_NAME = "release-manifest.json"
README_NAME = "README-DEPLOYMENT.txt"
WHEELHOUSE_MANIFEST = "backend/wheelhouse/wheelhouse-manifest.json"
FORMAT_VERSION = 1
MAX_PACKAGE_BYTES = 1024 * 1024 * 1024
MAX_PACKAGE_FILES = 10_000
SOURCE_PREFIXES = (
    "backend/app/",
    "backend/migrations/",
)
SOURCE_FILES = {
    "backend/alembic.ini",
    "backend/requirements.txt",
    "backend/scripts/audit_outsource_legacy_status.py",
    "backend/scripts/backup_mes.py",
    "backend/scripts/check_mes_operations.py",
    "backend/scripts/configure_postgres_monitoring.py",
    "backend/scripts/create_vendor_portal_user.py",
    "backend/scripts/mes_backup_common.py",
    "backend/scripts/rebuild_production_progress_snapshots.py",
    "backend/scripts/rewrite_lot_numbers_to_month_code.py",
    "backend/scripts/verify_mes_restore.py",
    "backend/scripts/verify_python_runtime.py",
    "deploy/windows/Prepare-MesPythonRuntime.ps1",
    "deploy/windows/Invoke-MesDeployment.ps1",
    "deploy/windows/Invoke-MesScheduledOperation.ps1",
    "deploy/windows/Install-MesRelease.ps1",
    "deploy/windows/MesDeployment.Common.ps1",
    "deploy/windows/MesRelease.Installation.Common.ps1",
    "deploy/windows/MesPythonRuntime.Common.ps1",
    "deploy/windows/Set-MesOperationsScheduledTasks.ps1",
    "deploy/windows/Test-MesDeployment.ps1",
    "deploy/windows/Test-MesReleaseInstallation.ps1",
    "deploy/windows/Test-MesRuntimeRehearsal.ps1",
    "deploy/windows/mes-deployment.example.psd1",
}
REQUIRED_FILES = {
    "backend/alembic.ini",
    "backend/requirements.txt",
    WHEELHOUSE_MANIFEST,
    "backend/app/main.py",
    "backend/migrations/env.py",
    "backend/scripts/backup_mes.py",
    "backend/scripts/check_mes_operations.py",
    "backend/scripts/verify_python_runtime.py",
    "deploy/windows/Invoke-MesDeployment.ps1",
    "deploy/windows/Install-MesRelease.ps1",
    "deploy/windows/MesRelease.Installation.Common.ps1",
    "deploy/windows/MesPythonRuntime.Common.ps1",
    "deploy/windows/Prepare-MesPythonRuntime.ps1",
    "deploy/windows/Test-MesDeployment.ps1",
    "deploy/windows/Test-MesReleaseInstallation.ps1",
    "deploy/windows/Test-MesRuntimeRehearsal.ps1",
    "clients/internal/Mes.Wpf.exe",
    "clients/internal/Mes.Wpf.dll",
    "clients/internal/Mes.Wpf.deps.json",
    "clients/internal/Mes.Wpf.runtimeconfig.json",
    "clients/internal/appsettings.Production.json",
    "clients/vendor/Mes.Vendor.Wpf.exe",
    "clients/vendor/Mes.Vendor.Wpf.dll",
    "clients/vendor/Mes.Vendor.Wpf.deps.json",
    "clients/vendor/Mes.Vendor.Wpf.runtimeconfig.json",
    "clients/vendor/appsettings.Production.json",
    README_NAME,
}
FORBIDDEN_FILE_NAMES = {
    ".env",
    ".env.example",
    "appsettings.json",
    "appsettings.development.json",
}
FORBIDDEN_SUFFIXES = {".key", ".p12", ".pdb", ".pem", ".pfx", ".pyc", ".pyo"}
FORBIDDEN_PARTS = {".git", ".pytest_cache", "__pycache__", "tests"}


class PackageValidationError(RuntimeError):
    pass


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
        raise PackageValidationError(
            f"Git command failed: {' '.join(arguments)}"
        )
    return process.stdout.strip()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative_path(value: str) -> PurePosixPath:
    if not value or "\\" in value:
        raise PackageValidationError(f"Unsafe package path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise PackageValidationError(f"Unsafe package path: {value!r}")
    return path


def _is_release_source(relative: str) -> bool:
    path = PurePosixPath(relative)
    lowered_parts = {part.lower() for part in path.parts}
    if lowered_parts & FORBIDDEN_PARTS:
        return False
    if path.suffix.lower() in {".pyc", ".pyo"}:
        return False
    return relative in SOURCE_FILES or relative.startswith(SOURCE_PREFIXES)


def select_release_source_files(tracked_files: Iterable[str]) -> list[str]:
    selected = sorted(
        relative
        for relative in tracked_files
        if relative and _is_release_source(relative)
    )
    missing = sorted(SOURCE_FILES.difference(selected))
    if missing:
        raise PackageValidationError(
            "Required tracked release source is missing: " + ", ".join(missing)
        )
    return selected


def stage_release_source(
    repository_root: Path,
    staging_root: Path,
    commit: str,
) -> list[str]:
    head = _run_git(repository_root, "rev-parse", "HEAD")
    if head != commit:
        raise PackageValidationError("Requested commit does not match Git HEAD")
    if _run_git(repository_root, "status", "--porcelain"):
        raise PackageValidationError("Git worktree must be clean before packaging")

    tracked = _run_git(repository_root, "ls-files", "-z").split("\0")
    selected = select_release_source_files(tracked)
    for relative in selected:
        source = repository_root / Path(relative)
        if source.is_symlink() or not source.is_file():
            raise PackageValidationError(
                f"Release source must be a regular file: {relative}"
            )
        destination = staging_root / Path(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return selected


def _iter_directory_files(root: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise PackageValidationError(
                f"Package must not contain links: {path.relative_to(root)}"
            )
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            _safe_relative_path(relative)
            files[relative] = path.read_bytes()
    return files


def _read_zip_files(path: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    total_size = 0
    with zipfile.ZipFile(path, "r") as archive:
        entries = archive.infolist()
        if len(entries) > MAX_PACKAGE_FILES:
            raise PackageValidationError("Package contains too many ZIP entries")
        for entry in entries:
            relative = entry.filename
            _safe_relative_path(relative)
            if relative.endswith("/"):
                continue
            if relative in files:
                raise PackageValidationError(
                    f"Package contains a duplicate ZIP entry: {relative}"
                )
            total_size += entry.file_size
            if total_size > MAX_PACKAGE_BYTES:
                raise PackageValidationError("Package uncompressed size is too large")
            files[relative] = archive.read(entry)
    return files


def _forbidden_paths(paths: Iterable[str]) -> list[str]:
    findings: list[str] = []
    for relative in paths:
        path = PurePosixPath(relative)
        lowered_parts = {part.lower() for part in path.parts}
        if (
            path.name.lower() in FORBIDDEN_FILE_NAMES
            or path.suffix.lower() in FORBIDDEN_SUFFIXES
            or lowered_parts & FORBIDDEN_PARTS
        ):
            findings.append(relative)
    return sorted(findings)


def _secret_findings(files: Mapping[str, bytes]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for relative, raw in files.items():
        if PurePosixPath(relative).suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for pattern_name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append({"path": relative, "pattern": pattern_name})
    return findings


def _validate_production_settings(files: Mapping[str, bytes]) -> None:
    for relative, vendor in (
        ("clients/internal/appsettings.Production.json", False),
        ("clients/vendor/appsettings.Production.json", True),
    ):
        try:
            payload = json.loads(files[relative].decode("utf-8"))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PackageValidationError(
                f"Invalid packaged Production settings: {relative}"
            ) from exc
        api = payload.get("Api") if isinstance(payload, dict) else None
        if not isinstance(api, dict):
            raise PackageValidationError(
                f"Packaged Production Api settings are missing: {relative}"
            )
        errors = _validate_base_url(
            str(api.get("BaseUrl", "")).strip(),
            vendor=vendor,
        )
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
                errors.append("Packaged API timeouts are not ordered")
        if _sensitive_key_paths(payload):
            errors.append("Packaged settings contain sensitive key names")
        if errors:
            raise PackageValidationError(
                f"Packaged Production settings are invalid: {relative}"
            )


def _parse_pinned_requirements(raw: bytes) -> list[tuple[str, str]]:
    try:
        if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
            text = raw.decode("utf-16")
        else:
            text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise PackageValidationError(
            "requirements.txt must be UTF-8 or BOM-marked UTF-16"
        ) from exc
    requirements: list[tuple[str, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s;]+)", value)
        if not match:
            raise PackageValidationError(
                f"Requirement line {line_number} is not exactly pinned"
            )
        requirements.append((match.group(1), match.group(2)))
    if not requirements:
        raise PackageValidationError("requirements.txt contains no packages")
    return requirements


def prepare_wheelhouse_manifest(
    requirements_path: Path,
    wheelhouse: Path,
) -> dict[str, object]:
    requirements_raw = requirements_path.read_bytes()
    requirements = _parse_pinned_requirements(requirements_raw)
    manifest_path = wheelhouse / "wheelhouse-manifest.json"
    if manifest_path.exists():
        raise PackageValidationError("Wheelhouse manifest already exists")
    unexpected = sorted(
        path.name
        for path in wheelhouse.iterdir()
        if not path.is_file() or path.suffix.lower() != ".whl"
    )
    if unexpected:
        raise PackageValidationError(
            "Wheelhouse contains unexpected entries: " + ", ".join(unexpected)
        )
    wheels = sorted(wheelhouse.glob("*.whl"), key=lambda path: path.name.lower())
    if not wheels:
        raise PackageValidationError("Wheelhouse contains no wheels")
    payload: dict[str, object] = {
        "format_version": 1,
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "major_minor": f"{sys.version_info.major}.{sys.version_info.minor}",
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "requirements_sha256": _sha256_bytes(requirements_raw),
        "requirement_count": len(requirements),
        "wheel_count": len(wheels),
        "wheels": [
            {
                "filename": path.name,
                "size": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
            for path in wheels
        ],
    }
    _write_json_atomic(manifest_path, payload)
    return payload


def _validate_wheelhouse_files(files: Mapping[str, bytes]) -> dict[str, object]:
    try:
        requirements_raw = files["backend/requirements.txt"]
        manifest = json.loads(files[WHEELHOUSE_MANIFEST].decode("utf-8"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageValidationError("Wheelhouse manifest is missing or invalid") from exc
    requirements = _parse_pinned_requirements(requirements_raw)
    if (
        not isinstance(manifest, dict)
        or manifest.get("format_version") != 1
        or manifest.get("requirements_sha256") != _sha256_bytes(requirements_raw)
        or manifest.get("requirement_count") != len(requirements)
    ):
        raise PackageValidationError("Wheelhouse metadata does not match requirements")
    python_metadata = manifest.get("python")
    if (
        not isinstance(python_metadata, dict)
        or python_metadata.get("implementation") != "CPython"
        or not re.fullmatch(r"\d+\.\d+", str(python_metadata.get("major_minor", "")))
        or python_metadata.get("system") != "Windows"
    ):
        raise PackageValidationError("Wheelhouse Python target is invalid")
    raw_wheels = manifest.get("wheels")
    if not isinstance(raw_wheels, list) or manifest.get("wheel_count") != len(raw_wheels):
        raise PackageValidationError("Wheelhouse file list is invalid")
    expected: dict[str, dict[str, object]] = {}
    for entry in raw_wheels:
        if not isinstance(entry, dict):
            raise PackageValidationError("Wheelhouse contains an invalid file entry")
        filename = str(entry.get("filename", ""))
        if (
            not filename
            or PurePosixPath(filename).name != filename
            or not filename.lower().endswith(".whl")
            or filename in expected
        ):
            raise PackageValidationError("Wheelhouse contains an unsafe wheel name")
        expected[filename] = entry
    actual = {
        relative.removeprefix("backend/wheelhouse/"): raw
        for relative, raw in files.items()
        if relative.startswith("backend/wheelhouse/")
        and relative != WHEELHOUSE_MANIFEST
    }
    if set(actual) != set(expected):
        raise PackageValidationError("Wheelhouse contents do not match its manifest")
    for filename, raw in actual.items():
        entry = expected[filename]
        if entry.get("size") != len(raw) or entry.get("sha256") != _sha256_bytes(raw):
            raise PackageValidationError(f"Wheelhouse hash mismatch: {filename}")
    return manifest


def _parse_manifest(files: Mapping[str, bytes]) -> dict[str, object]:
    try:
        manifest = json.loads(files[MANIFEST_NAME].decode("utf-8"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageValidationError("Release manifest is missing or invalid") from exc
    if not isinstance(manifest, dict) or manifest.get("format_version") != FORMAT_VERSION:
        raise PackageValidationError("Release manifest format is unsupported")
    return manifest


def validate_package_files(
    files: Mapping[str, bytes],
    *,
    expected_commit: str | None = None,
) -> dict[str, object]:
    if len(files) > MAX_PACKAGE_FILES:
        raise PackageValidationError("Package contains too many files")
    if sum(len(value) for value in files.values()) > MAX_PACKAGE_BYTES:
        raise PackageValidationError("Package uncompressed size is too large")

    forbidden = _forbidden_paths(files)
    if forbidden:
        raise PackageValidationError(
            "Package contains forbidden paths: " + ", ".join(forbidden)
        )
    missing = sorted(REQUIRED_FILES.difference(files))
    if missing:
        raise PackageValidationError(
            "Package is missing required files: " + ", ".join(missing)
        )
    if not any(
        relative.startswith("backend/migrations/versions/")
        and relative.endswith(".py")
        for relative in files
    ):
        raise PackageValidationError("Package contains no Alembic revisions")

    manifest = _parse_manifest(files)
    git_metadata = manifest.get("git")
    if not isinstance(git_metadata, dict):
        raise PackageValidationError("Release manifest Git metadata is invalid")
    commit = str(git_metadata.get("commit", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise PackageValidationError("Release manifest commit is invalid")
    if expected_commit and commit != expected_commit:
        raise PackageValidationError("Package commit does not match expected commit")

    manifest_files = manifest.get("files")
    if not isinstance(manifest_files, list):
        raise PackageValidationError("Release manifest file list is invalid")
    expected_entries: dict[str, dict[str, object]] = {}
    for entry in manifest_files:
        if not isinstance(entry, dict):
            raise PackageValidationError("Release manifest file entry is invalid")
        relative = str(entry.get("path", ""))
        _safe_relative_path(relative)
        if relative == MANIFEST_NAME or relative in expected_entries:
            raise PackageValidationError("Release manifest has a duplicate file entry")
        expected_entries[relative] = entry

    actual_paths = set(files).difference({MANIFEST_NAME})
    if actual_paths != set(expected_entries):
        raise PackageValidationError(
            "Package contents do not exactly match the release manifest"
        )
    for relative, entry in expected_entries.items():
        raw = files[relative]
        if entry.get("size") != len(raw) or entry.get("sha256") != _sha256_bytes(raw):
            raise PackageValidationError(
                f"Package file hash or size mismatch: {relative}"
            )

    secrets = _secret_findings(files)
    if secrets:
        labels = ", ".join(
            f"{item['path']} ({item['pattern']})" for item in secrets
        )
        raise PackageValidationError(
            "Package contains a high-confidence secret pattern: " + labels
        )
    _validate_production_settings(files)
    _validate_wheelhouse_files(files)
    return manifest


def validate_package(
    package_path: Path,
    *,
    expected_commit: str | None = None,
) -> dict[str, object]:
    files = (
        _iter_directory_files(package_path)
        if package_path.is_dir()
        else _read_zip_files(package_path)
    )
    return validate_package_files(files, expected_commit=expected_commit)


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _commit_zip_timestamp(commit_timestamp: str) -> tuple[int, int, int, int, int, int]:
    parsed = datetime.fromisoformat(commit_timestamp.replace("Z", "+00:00"))
    parsed = parsed.astimezone(timezone.utc)
    if parsed.year < 1980:
        parsed = parsed.replace(year=1980)
    return (
        parsed.year,
        parsed.month,
        parsed.day,
        parsed.hour,
        parsed.minute,
        parsed.second - (parsed.second % 2),
    )


def _validation_evidence_sha256(report: Mapping[str, object]) -> str:
    raw_results = report.get("results")
    if not isinstance(raw_results, list):
        raise PackageValidationError("Release validation report results are invalid")
    results: list[dict[str, object]] = []
    for result in raw_results:
        if not isinstance(result, dict):
            raise PackageValidationError(
                "Release validation report contains an invalid result"
            )
        results.append(
            {
                "name": result.get("name"),
                "status": result.get("status"),
                "summary": result.get("summary"),
            }
        )
    evidence = {
        "format_version": report.get("format_version"),
        "overall_status": report.get("overall_status"),
        "commit": report.get("commit"),
        "clean_worktree_required": report.get("clean_worktree_required"),
        "dotnet_restore_skipped": report.get("dotnet_restore_skipped"),
        "results": results,
    }
    encoded = json.dumps(
        evidence,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return _sha256_bytes(encoded)


def _write_deterministic_zip(
    staging_root: Path,
    output_zip: Path,
    commit_timestamp: str,
) -> None:
    timestamp = _commit_zip_timestamp(commit_timestamp)
    temporary = output_zip.with_name(f".{output_zip.name}.tmp")
    with zipfile.ZipFile(
        temporary,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(staging_root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(staging_root).as_posix()
            info = zipfile.ZipInfo(relative, date_time=timestamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    os.replace(temporary, output_zip)


def finalize_package(
    staging_root: Path,
    output_zip: Path,
    *,
    commit: str,
    branch: str,
    commit_timestamp: str,
    alembic_head: str,
    validation_report: Path,
) -> dict[str, object]:
    for path in (
        output_zip,
        output_zip.with_suffix(".manifest.json"),
        output_zip.with_suffix(".sha256"),
    ):
        if path.exists():
            raise PackageValidationError(f"Release output already exists: {path}")
    if (staging_root / MANIFEST_NAME).exists():
        raise PackageValidationError("Staging root already contains a release manifest")

    report = json.loads(validation_report.read_text(encoding="utf-8-sig"))
    if report.get("overall_status") != "OK" or report.get("commit") != commit:
        raise PackageValidationError(
            "Release validation report is not successful for this commit"
        )

    readme = (
        "MES V2 RELEASE PACKAGE\n"
        f"Git commit: {commit}\n"
        f"Alembic head: {alembic_head}\n\n"
        "Extract the package to a new versioned directory.\n"
        "Do not place backend.env or monitor.env inside this directory.\n"
        "The WPF clients require the Microsoft .NET 8 Desktop Runtime (x64).\n"
        "The backend wheelhouse targets the Python runtime recorded in the manifest.\n"
        "Prepare backend/.venv with Prepare-MesPythonRuntime.ps1 before activation.\n"
        "Run the documented deployment preflight before changing server state.\n"
        "Rehearse installation, runtime startup, and pointer rollback before activation.\n"
    )
    (staging_root / README_NAME).write_text(readme, encoding="ascii")

    staged_files = _iter_directory_files(staging_root)
    forbidden = _forbidden_paths(staged_files)
    if forbidden:
        raise PackageValidationError(
            "Staging root contains forbidden paths: " + ", ".join(forbidden)
        )
    missing = sorted(REQUIRED_FILES.difference(staged_files))
    if missing:
        raise PackageValidationError(
            "Staging root is missing required files: " + ", ".join(missing)
        )
    secrets = _secret_findings(staged_files)
    if secrets:
        raise PackageValidationError(
            "Staging root contains a high-confidence secret pattern"
        )
    _validate_production_settings(staged_files)
    wheelhouse_manifest = _validate_wheelhouse_files(staged_files)

    manifest: dict[str, object] = {
        "format_version": FORMAT_VERSION,
        "release_type": "mes-v2-windows",
        "git": {
            "commit": commit,
            "short_commit": commit[:8],
            "branch": branch,
            "commit_timestamp_utc": commit_timestamp,
        },
        "database": {"alembic_head": alembic_head},
        "validation": {
            "evidence_sha256": _validation_evidence_sha256(report),
            "overall_status": "OK",
        },
        "clients": {
            "deployment_mode": "framework-dependent",
            "target_framework": "net8.0-windows",
            "required_runtime": "Microsoft .NET 8 Desktop Runtime (x64)",
        },
        "python_runtime": wheelhouse_manifest["python"],
        "entry_points": {
            "backend": "backend/app/main.py",
            "internal_client": "clients/internal/Mes.Wpf.exe",
            "vendor_client": "clients/vendor/Mes.Vendor.Wpf.exe",
            "deployment_preflight": "deploy/windows/Test-MesDeployment.ps1",
        },
        "files": [
            {
                "path": relative,
                "size": len(raw),
                "sha256": _sha256_bytes(raw),
            }
            for relative, raw in sorted(staged_files.items())
        ],
    }
    _write_json_atomic(staging_root / MANIFEST_NAME, manifest)
    validate_package(staging_root, expected_commit=commit)

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    _write_deterministic_zip(staging_root, output_zip, commit_timestamp)
    validate_package(output_zip, expected_commit=commit)

    sidecar_manifest = output_zip.with_suffix(".manifest.json")
    shutil.copyfile(staging_root / MANIFEST_NAME, sidecar_manifest)
    package_hash = _sha256_file(output_zip)
    output_zip.with_suffix(".sha256").write_text(
        f"{package_hash}  {output_zip.name}\n",
        encoding="ascii",
    )
    return {
        "status": "OK",
        "package": str(output_zip),
        "package_sha256": package_hash,
        "manifest": str(sidecar_manifest),
        "file_count": len(staged_files) + 1,
        "commit": commit,
        "alembic_head": alembic_head,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and validate MES V2 packages.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    stage = subparsers.add_parser("stage-source")
    stage.add_argument("--repository-root", type=Path, required=True)
    stage.add_argument("--staging-root", type=Path, required=True)
    stage.add_argument("--commit", required=True)

    finalize = subparsers.add_parser("finalize")
    finalize.add_argument("--staging-root", type=Path, required=True)
    finalize.add_argument("--output-zip", type=Path, required=True)
    finalize.add_argument("--commit", required=True)
    finalize.add_argument("--branch", required=True)
    finalize.add_argument("--commit-timestamp", required=True)
    finalize.add_argument("--alembic-head", required=True)
    finalize.add_argument("--validation-report", type=Path, required=True)

    wheelhouse = subparsers.add_parser("prepare-wheelhouse")
    wheelhouse.add_argument("--requirements", type=Path, required=True)
    wheelhouse.add_argument("--wheelhouse", type=Path, required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--package", type=Path, required=True)
    validate.add_argument("--expected-commit")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "stage-source":
        selected = stage_release_source(
            args.repository_root.resolve(strict=True),
            args.staging_root.resolve(strict=True),
            args.commit,
        )
        result: Mapping[str, object] = {
            "status": "OK",
            "staged_source_files": len(selected),
        }
    elif args.command == "prepare-wheelhouse":
        manifest = prepare_wheelhouse_manifest(
            args.requirements.resolve(strict=True),
            args.wheelhouse.resolve(strict=True),
        )
        result = {
            "status": "OK",
            "wheel_count": manifest["wheel_count"],
            "python": manifest["python"],
        }
    elif args.command == "finalize":
        result = finalize_package(
            args.staging_root.resolve(strict=True),
            args.output_zip.resolve(),
            commit=args.commit,
            branch=args.branch,
            commit_timestamp=args.commit_timestamp,
            alembic_head=args.alembic_head,
            validation_report=args.validation_report.resolve(strict=True),
        )
    else:
        manifest = validate_package(
            args.package.resolve(strict=True),
            expected_commit=args.expected_commit,
        )
        result = {
            "status": "OK",
            "package": str(args.package.resolve()),
            "commit": manifest["git"]["commit"],
            "file_count": len(manifest["files"]) + 1,
        }
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"release_package_failed={type(exc).__name__}", file=sys.stderr)
        raise SystemExit(2) from exc
