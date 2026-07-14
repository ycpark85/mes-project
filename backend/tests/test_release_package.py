from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.release_package import (
    MANIFEST_NAME,
    PackageValidationError,
    _sha256_bytes,
    finalize_package,
    prepare_wheelhouse_manifest,
    select_release_source_files,
    validate_package,
    validate_package_files,
)


COMMIT = "a" * 40


def _minimum_files() -> dict[str, bytes]:
    requirements = b"fastapi==1\n"
    wheel_name = "fastapi-1-py3-none-any.whl"
    wheel_raw = b"test-wheel"
    wheelhouse_manifest = json.dumps(
        {
            "format_version": 1,
            "python": {
                "implementation": "CPython",
                "version": "3.14.6",
                "major_minor": "3.14",
                "system": "Windows",
                "machine": "AMD64",
            },
            "requirements_sha256": hashlib.sha256(requirements).hexdigest(),
            "requirement_count": 1,
            "wheel_count": 1,
            "wheels": [
                {
                    "filename": wheel_name,
                    "size": len(wheel_raw),
                    "sha256": hashlib.sha256(wheel_raw).hexdigest(),
                }
            ],
        }
    ).encode()
    files = {
        "backend/alembic.ini": b"[alembic]\n",
        "backend/requirements.txt": requirements,
        f"backend/wheelhouse/{wheel_name}": wheel_raw,
        "backend/wheelhouse/wheelhouse-manifest.json": wheelhouse_manifest,
        "backend/app/main.py": b"app = object()\n",
        "backend/migrations/env.py": b"# migration env\n",
        "backend/migrations/versions/abc_revision.py": b"revision = 'abc'\n",
        "backend/scripts/backup_mes.py": b"# backup\n",
        "backend/scripts/check_mes_operations.py": b"# monitor\n",
        "backend/scripts/verify_python_runtime.py": b"# runtime verification\n",
        "deploy/windows/Invoke-MesDeployment.ps1": b"# deployment\n",
        "deploy/windows/Invoke-MesReleaseActivation.ps1": b"# activation\n",
        "deploy/windows/Install-MesRelease.ps1": b"# installer\n",
        "deploy/windows/MesRelease.Installation.Common.ps1": b"# install common\n",
        "deploy/windows/MesRelease.Activation.Common.ps1": b"# activation common\n",
        "deploy/windows/MesPythonRuntime.Common.ps1": b"# runtime common\n",
        "deploy/windows/Prepare-MesPythonRuntime.ps1": b"# runtime preparation\n",
        "deploy/windows/Test-MesDeployment.ps1": b"# preflight\n",
        "deploy/windows/Test-MesReleaseInstallation.ps1": b"# rehearsal\n",
        "deploy/windows/Test-MesReleaseActivationRehearsal.ps1": b"# activation rehearsal\n",
        "deploy/windows/Test-MesGoLiveReadiness.ps1": b"# go-live evidence\n",
        "deploy/windows/Test-MesRuntimeRehearsal.ps1": b"# runtime rehearsal\n",
        "clients/internal/Mes.Wpf.exe": b"internal-exe",
        "clients/internal/Mes.Wpf.dll": b"internal-dll",
        "clients/internal/Mes.Wpf.deps.json": b"{}",
        "clients/internal/Mes.Wpf.runtimeconfig.json": b"{}",
        "clients/internal/appsettings.Production.json": json.dumps(
            {
                "Api": {
                    "BaseUrl": "http://172.30.1.240:8000/",
                    "NormalTimeoutSeconds": 45,
                    "BulkTimeoutSeconds": 150,
                    "FileTransferTimeoutSeconds": 300,
                }
            }
        ).encode(),
        "clients/vendor/Mes.Vendor.Wpf.exe": b"vendor-exe",
        "clients/vendor/Mes.Vendor.Wpf.dll": b"vendor-dll",
        "clients/vendor/Mes.Vendor.Wpf.deps.json": b"{}",
        "clients/vendor/Mes.Vendor.Wpf.runtimeconfig.json": b"{}",
        "clients/vendor/appsettings.Production.json": json.dumps(
            {
                "Api": {
                    "BaseUrl": "https://vendor.example.com/",
                    "NormalTimeoutSeconds": 45,
                }
            }
        ).encode(),
        "README-DEPLOYMENT.txt": b"release instructions\n",
    }
    manifest = {
        "format_version": 1,
        "git": {"commit": COMMIT},
        "files": [
            {
                "path": relative,
                "size": len(raw),
                "sha256": _sha256_bytes(raw),
            }
            for relative, raw in sorted(files.items())
        ],
    }
    files[MANIFEST_NAME] = json.dumps(manifest).encode()
    return files


class ReleaseSourceSelectionTests(unittest.TestCase):
    def test_only_runtime_and_operations_source_is_selected(self) -> None:
        tracked = [
            *sorted(
                {
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
                    "deploy/windows/Invoke-MesDeployment.ps1",
                    "deploy/windows/Invoke-MesReleaseActivation.ps1",
                    "deploy/windows/Invoke-MesScheduledOperation.ps1",
                    "deploy/windows/Install-MesRelease.ps1",
                    "deploy/windows/MesDeployment.Common.ps1",
                    "deploy/windows/MesPythonRuntime.Common.ps1",
                    "deploy/windows/MesRelease.Installation.Common.ps1",
                    "deploy/windows/MesRelease.Activation.Common.ps1",
                    "deploy/windows/Prepare-MesPythonRuntime.ps1",
                    "deploy/windows/Set-MesOperationsScheduledTasks.ps1",
                    "deploy/windows/Test-MesDeployment.ps1",
                    "deploy/windows/Test-MesReleaseInstallation.ps1",
                    "deploy/windows/Test-MesReleaseActivationRehearsal.ps1",
                    "deploy/windows/Test-MesGoLiveReadiness.ps1",
                    "deploy/windows/Test-MesRuntimeRehearsal.ps1",
                    "deploy/windows/mes-deployment.example.psd1",
                }
            ),
            "backend/app/main.py",
            "backend/app/__pycache__/main.pyc",
            "backend/migrations/env.py",
            "backend/tests/test_main.py",
            "backend/.env.example",
            "backend/scripts/release_package.py",
            "deploy/windows/New-MesReleasePackage.ps1",
        ]

        selected = select_release_source_files(tracked)

        self.assertIn("backend/app/main.py", selected)
        self.assertNotIn("backend/app/__pycache__/main.pyc", selected)
        self.assertNotIn("backend/tests/test_main.py", selected)
        self.assertNotIn("backend/.env.example", selected)
        self.assertNotIn("backend/scripts/release_package.py", selected)
        self.assertNotIn("deploy/windows/New-MesReleasePackage.ps1", selected)


class ReleasePackageValidationTests(unittest.TestCase):
    def test_wheelhouse_manifest_records_file_hashes_and_python_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            requirements = root / "requirements.txt"
            requirements.write_text("example-package==1.2.3\n", encoding="utf-16")
            wheelhouse = root / "wheelhouse"
            wheelhouse.mkdir()
            wheel = wheelhouse / "example_package-1.2.3-py3-none-any.whl"
            wheel.write_bytes(b"wheel-content")

            manifest = prepare_wheelhouse_manifest(requirements, wheelhouse)

            self.assertEqual(1, manifest["wheel_count"])
            self.assertEqual("CPython", manifest["python"]["implementation"])
            self.assertEqual(
                hashlib.sha256(wheel.read_bytes()).hexdigest(),
                manifest["wheels"][0]["sha256"],
            )

    def test_valid_package_files_are_accepted(self) -> None:
        manifest = validate_package_files(
            _minimum_files(),
            expected_commit=COMMIT,
        )

        self.assertEqual(COMMIT, manifest["git"]["commit"])

    def test_tampered_file_is_rejected(self) -> None:
        files = _minimum_files()
        files["backend/app/main.py"] = b"tampered\n"

        with self.assertRaisesRegex(PackageValidationError, "hash or size"):
            validate_package_files(files)

    def test_tampered_wheel_is_rejected_even_when_release_manifest_is_updated(self) -> None:
        files = _minimum_files()
        relative = "backend/wheelhouse/fastapi-1-py3-none-any.whl"
        raw = b"different-wheel"
        files[relative] = raw
        manifest = json.loads(files[MANIFEST_NAME])
        entry = next(item for item in manifest["files"] if item["path"] == relative)
        entry["size"] = len(raw)
        entry["sha256"] = _sha256_bytes(raw)
        files[MANIFEST_NAME] = json.dumps(manifest).encode()

        with self.assertRaisesRegex(PackageValidationError, "Wheelhouse hash mismatch"):
            validate_package_files(files)

    def test_development_settings_are_rejected(self) -> None:
        files = _minimum_files()
        files["clients/internal/appsettings.Development.json"] = b"{}"

        with self.assertRaisesRegex(PackageValidationError, "forbidden paths"):
            validate_package_files(files)

    def test_insecure_vendor_settings_are_rejected(self) -> None:
        files = _minimum_files()
        relative = "clients/vendor/appsettings.Production.json"
        raw = json.dumps(
            {
                "Api": {
                    "BaseUrl": "http://vendor.example.com/",
                    "NormalTimeoutSeconds": 45,
                }
            }
        ).encode()
        files[relative] = raw
        manifest = json.loads(files[MANIFEST_NAME])
        entry = next(item for item in manifest["files"] if item["path"] == relative)
        entry["size"] = len(raw)
        entry["sha256"] = _sha256_bytes(raw)
        files[MANIFEST_NAME] = json.dumps(manifest).encode()

        with self.assertRaisesRegex(PackageValidationError, "settings are invalid"):
            validate_package_files(files)

    def test_zip_path_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            archive_path = Path(temp_directory) / "unsafe.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../outside.txt", "unsafe")

            with self.assertRaisesRegex(PackageValidationError, "Unsafe package path"):
                validate_package(archive_path)

    def test_finalize_creates_reproducible_validated_zip_and_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            report = root / "release-validation.json"
            report.write_text(
                json.dumps(
                    {
                        "format_version": 1,
                        "overall_status": "OK",
                        "commit": COMMIT,
                        "clean_worktree_required": True,
                        "dotnet_restore_skipped": False,
                        "results": [
                            {
                                "name": "backend_tests",
                                "status": "OK",
                                "duration_seconds": 1.25,
                                "summary": "Command completed with exit code 0",
                                "log_path": "C:/first/run/backend_tests.log",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            package_hashes: list[str] = []
            for index in range(2):
                staging = root / f"staging-{index}"
                files = _minimum_files()
                files.pop(MANIFEST_NAME)
                for relative, raw in files.items():
                    path = staging / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(raw)
                output = root / f"release-{index}.zip"

                result = finalize_package(
                    staging,
                    output,
                    commit=COMMIT,
                    branch="release/test",
                    commit_timestamp="2026-07-14T02:39:38Z",
                    alembic_head="abc",
                    validation_report=report,
                )

                self.assertTrue(output.is_file())
                self.assertTrue(output.with_suffix(".manifest.json").is_file())
                self.assertTrue(output.with_suffix(".sha256").is_file())
                validate_package(output, expected_commit=COMMIT)
                package_hashes.append(result["package_sha256"])
                report_payload = json.loads(report.read_text(encoding="utf-8"))
                report_payload["generated_at_utc"] = f"2026-07-14T02:40:0{index}Z"
                report_payload["results"][0]["duration_seconds"] = 2.5 + index
                report_payload["results"][0]["log_path"] = (
                    f"C:/different/run-{index}/backend_tests.log"
                )
                report.write_text(json.dumps(report_payload), encoding="utf-8")
            self.assertEqual(package_hashes[0], package_hashes[1])


if __name__ == "__main__":
    unittest.main()
