# MES V2 Release Installation Rehearsal

## Purpose

The installation rehearsal proves that an approved release ZIP can be verified, installed without overwriting another version, activated through a version pointer, explicitly rolled back, and automatically recovered when a pointer switch fails. It runs in an isolated directory and does not connect to PostgreSQL, change a Windows service, read production env files, or change production configuration.

The V2 server layout is:

```text
C:\MES\v2\
  current -> releases\<active-full-git-commit>
  releases\
    <full-git-commit>\
      backend\
      deploy\windows\
      clients\
      release-manifest.json
```

`current` is an NTFS directory junction. Deployment configuration, the API service, and scheduled tasks use paths under `C:\MES\v2\current`. A release directory is immutable after verified installation.

## Verified Staging

`deploy/windows/Install-MesRelease.ps1` performs staging only. It verifies the package SHA-256 sidecar, sidecar and embedded manifests, safe ZIP paths, entry uniqueness, expansion limits, exact file list, every file size and SHA-256, required runtime files, commit, and validation status before extraction.

Extraction goes to a temporary directory below `releases`. Every extracted file is verified again before the directory is atomically renamed to its full Git commit. An existing matching release is validated and reported as `ALREADY_STAGED`; it is never overwritten.

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass `
  -File .\deploy\windows\Install-MesRelease.ps1 `
  -PackagePath E:\MES\release-packages\mes-v2-01234567.zip `
  -ManifestPath E:\MES\release-packages\mes-v2-01234567.manifest.json `
  -ChecksumPath E:\MES\release-packages\mes-v2-01234567.sha256 `
  -ReleaseRoot C:\MES\v2
```

This command does not create the Python virtual environment and does not change `current`. Prepare and test the runtime separately as documented in `docs/runtime-rehearsal.md`.

## Isolated Rehearsal

The rehearsal root must not already exist. Keep it outside the repository and production server root.

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass `
  -File .\deploy\windows\Test-MesReleaseInstallation.ps1 `
  -PackagePath E:\MES\release-packages\mes-v2-01234567.zip `
  -ManifestPath E:\MES\release-packages\mes-v2-01234567.manifest.json `
  -ChecksumPath E:\MES\release-packages\mes-v2-01234567.sha256 `
  -RehearsalRoot E:\MES\rehearsals\01234567
```

The rehearsal performs and records:

1. Create an isolated previous release and `current` junction.
2. Verify and install the real release package.
3. Switch `current` to the staged release.
4. Explicitly switch `current` back to the previous release.
5. Inject a failure after moving the current pointer and prove automatic restoration.
6. Confirm that no temporary junction remains and the previous release is active.

The final JSON report explicitly records that database, Windows services, and production configuration were not changed.

## Rollback Boundary

This rehearsal proves application-file pointer rollback only. It does not prove that a database schema can be downgraded. Never run an automatic Alembic downgrade during failure handling.

Before production activation, review every planned migration for backward compatibility with the previous application release. If a migration is not backward compatible, use the verified maintenance backup and an approved database recovery plan instead of switching application files alone. Production activation remains a separate approved maintenance operation.
