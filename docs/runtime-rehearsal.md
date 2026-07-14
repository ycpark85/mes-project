# MES V2 Python Runtime And API Rehearsal

## Purpose

The runtime rehearsal proves that the packaged backend dependencies can be installed offline and that the candidate API can answer liveness and database-readiness checks before the active release pointer is changed. It uses an isolated release root, a non-production env file, and a loopback-only API port.

It does not use the production database, run Alembic, execute FastAPI lifespan startup tasks, change a Windows service, change production configuration, or activate the candidate release.

## Offline Runtime Preparation

The release package contains `backend/wheelhouse`, its SHA-256 manifest, and exact versions in `backend/requirements.txt`. `Prepare-MesPythonRuntime.ps1` verifies all three before creating `backend/.venv`.

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass `
  -File C:\MES\v2\releases\<commit>\deploy\windows\Prepare-MesPythonRuntime.ps1 `
  -ReleasePath C:\MES\v2\releases\<commit> `
  -BootstrapPythonPath C:\Python314\python.exe
```

The bootstrap interpreter must match the packaged CPython major/minor version and machine architecture. Installation first uses a temporary directory, runs `pip check`, verifies every pinned installed version, and imports critical backend libraries. Only then is the directory renamed to `.venv`. An existing `.venv` is verified rather than overwritten.

## Isolated API Rehearsal

Use a new root outside the repository and production server root. The env file must not use `APP_ENV=prod` or `APP_ENV=production`, and its PostgreSQL host must be `localhost`, `127.0.0.1`, or `::1`.

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass `
  -File .\deploy\windows\Test-MesRuntimeRehearsal.ps1 `
  -PackagePath E:\MES\release-packages\mes-v2-01234567.zip `
  -ManifestPath E:\MES\release-packages\mes-v2-01234567.manifest.json `
  -ChecksumPath E:\MES\release-packages\mes-v2-01234567.sha256 `
  -BootstrapPythonPath C:\Python314\python.exe `
  -EnvFile C:\MES\rehearsal\backend.env `
  -RehearsalRoot E:\MES\runtime-rehearsals\01234567
```

The rehearsal performs and records:

1. Verify and stage the real release package beside a synthetic previous release.
2. Build and verify the candidate `.venv` using only the packaged wheelhouse.
3. Confirm runtime preparation did not change the `current` junction.
4. Start the candidate on loopback with FastAPI lifespan disabled.
5. Require `/api/v1/health` and `/api/v1/ready` to succeed against the local rehearsal database.
6. Inject an invalid API module startup and prove the previous release remains active.

The JSON report records the package hash, Python version, wheel count, checks, and explicit false values for production database use, migration, lifespan startup, Windows service changes, and production configuration changes.

## Safety Boundary

Readiness executes `SELECT 1` against the local rehearsal database. Disabling lifespan prevents startup seed/configuration work, but this rehearsal does not replace a migration rehearsal or production smoke test. Production activation still requires protected production settings, an approved backup, migration review, service control, and post-activation verification.
