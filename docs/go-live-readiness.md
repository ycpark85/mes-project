# MES V2 Go-Live Readiness Evidence

## Purpose

The final readiness check prevents reports from different source revisions or package files from being combined accidentally. It requires one exact Git commit and package SHA-256 across the release quality gate and all isolated rehearsals.

No production deployment is performed by this check.

## Required Evidence

- Successful integrated release-validation report.
- Verified installation and pointer-rollback rehearsal report.
- Offline Python runtime and API health/readiness rehearsal report.
- Successful activation and failed-candidate automatic rollback rehearsal report.
- Matching release ZIP, manifest sidecar, and checksum sidecar.

## Activation Rehearsal

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass `
  -File .\deploy\windows\Test-MesReleaseActivationRehearsal.ps1 `
  -PackagePath E:\MES\packages\mes-v2-01234567.zip `
  -ManifestPath E:\MES\packages\mes-v2-01234567.manifest.json `
  -ChecksumPath E:\MES\packages\mes-v2-01234567.sha256 `
  -BootstrapPythonPath C:\Python314\python.exe `
  -EnvFile C:\MES\rehearsal\backend.env `
  -RehearsalRoot E:\MES\activation-rehearsals\01234567
```

The env file must be non-production and use local PostgreSQL. FastAPI lifespan is disabled, so the database operation is limited to readiness `SELECT 1`. No Windows service, migration, or production configuration is changed.

## Final Evidence Check

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass `
  -File .\deploy\windows\Test-MesGoLiveReadiness.ps1 `
  -PackagePath E:\MES\packages\mes-v2-01234567.zip `
  -ManifestPath E:\MES\packages\mes-v2-01234567.manifest.json `
  -ChecksumPath E:\MES\packages\mes-v2-01234567.sha256 `
  -ExpectedCommit 0123456789abcdef0123456789abcdef01234567 `
  -ReleaseValidationReport E:\MES\evidence\release-validation.json `
  -InstallationRehearsalReport E:\MES\evidence\release-installation-rehearsal.json `
  -RuntimeRehearsalReport E:\MES\evidence\runtime-rehearsal.json `
  -ActivationRehearsalReport E:\MES\evidence\release-activation-rehearsal.json `
  -OutputReport E:\MES\evidence\go-live-readiness.json
```

`status=READY` means the local artifact and rehearsal evidence are internally consistent. It does not approve a maintenance date, production credentials, migration contents, network routing, or business-user acceptance; those remain explicit deployment decisions.
