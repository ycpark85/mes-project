# MES V2 Release Activation

## Purpose

`Invoke-MesReleaseActivation.ps1` connects an approved package to the production release pointer and API Windows service. Its default mode is read-only: it validates the package, configuration, active release, and deployment preflight without installing or switching anything.

The apply path requires an elevated PowerShell session and an explicit `-Apply` switch. It never runs PostgreSQL monitoring setup, restarts PostgreSQL, registers scheduled tasks, or performs an Alembic downgrade.

## Read-Only Plan

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass `
  -File C:\MES\v2\current\deploy\windows\Invoke-MesReleaseActivation.ps1 `
  -ConfigFile C:\MES\config\mes-deployment.psd1 `
  -PackagePath E:\MES\packages\mes-v2-01234567.zip `
  -ManifestPath E:\MES\packages\mes-v2-01234567.manifest.json `
  -ChecksumPath E:\MES\packages\mes-v2-01234567.sha256 `
  -ReleaseRoot C:\MES\v2 `
  -BootstrapPythonPath C:\Python314\python.exe
```

The configured `BackendRoot` and `PythonPath` must resolve through `<ReleaseRoot>\current`. The package commit must differ from the active release.

## Approved Activation

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass `
  -File C:\MES\v2\current\deploy\windows\Invoke-MesReleaseActivation.ps1 `
  -ConfigFile C:\MES\config\mes-deployment.psd1 `
  -PackagePath E:\MES\packages\mes-v2-01234567.zip `
  -ManifestPath E:\MES\packages\mes-v2-01234567.manifest.json `
  -ChecksumPath E:\MES\packages\mes-v2-01234567.sha256 `
  -ReleaseRoot C:\MES\v2 `
  -BootstrapPythonPath C:\Python314\python.exe `
  -Apply
```

The activation sequence is:

1. Run the read-only production preflight.
2. Verify and install the immutable package and prepare its offline Python runtime.
3. Reject broad write permissions on the candidate release.
4. Require the current API service to be healthy enough to serve as a rollback baseline.
5. Stop the API and create a verified maintenance backup.
6. Use the protected env file to verify the candidate Alembic head against the database.
7. Atomically switch `current`, start the API service, and require health and readiness.
8. If candidate startup or smoke testing fails, stop it, restore the previous pointer, restart the previous service, and verify it.

An activation report is stored under `<OperationsLogRoot>\deployments` and contains no secrets.

## Migration Boundary

Without `-ApplyMigration`, activation requires the database to already be at the candidate head. To apply a migration during the same maintenance window, both switches are required:

```powershell
-ApplyMigration -ApproveBackwardCompatibleMigration
```

The second switch is an operator assertion that the reviewed schema change still permits the previous application version to run if application rollback is required. The script does not infer backward compatibility and never automatically downgrades the database.

PostgreSQL monitoring setup and scheduled-task registration remain in `Invoke-MesDeployment.ps1` and should be completed in their separately approved maintenance steps.
