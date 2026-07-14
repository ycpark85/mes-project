# MES V2 Release Package

## Purpose

`deploy/windows/New-MesReleasePackage.ps1` creates the reviewed Windows release artifact for one clean Git commit. It always runs the complete release quality gate first. It does not copy files to the production server, create a virtual environment, apply a migration, change a service, or install a WPF client.

The package is framework-dependent. Internal and vendor client computers require the Microsoft .NET 8 Desktop Runtime for x64 Windows. The backend package includes version-pinned requirements and a verified Windows wheelhouse so its virtual environment can be prepared without downloading packages on the production server.

## Create A Package

Use an output directory outside the Git repository:

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass `
  -File .\deploy\windows\New-MesReleasePackage.ps1 `
  -RepositoryRoot C:\path\to\mes-v1 `
  -OutputRoot E:\MES\release-packages
```

The command refuses a dirty worktree, a detached branch, an output path inside the repository, multiple Alembic heads, failed quality checks, and an existing artifact with the same commit name. Existing release files are never overwritten implicitly.

## Package Contents

The ZIP contains:

- `backend`: FastAPI source, Alembic revisions, templates, pinned requirements, a hashed Windows wheelhouse, and approved operational scripts.
- `deploy/windows`: production preflight, deployment, scheduled operation, and shared Windows scripts.
- `clients/internal`: framework-dependent internal MES WPF publish output.
- `clients/vendor`: framework-dependent vendor WPF publish output.
- `release-manifest.json`: exact commit, branch, commit timestamp, Alembic head, normalized quality-evidence hash, .NET and Python runtime requirements, entry points, file sizes, and SHA-256 hashes.
- `README-DEPLOYMENT.txt`: short extraction and safety reminder.

The output directory also receives a manifest sidecar, a package SHA-256 sidecar, and the complete quality-gate report directory.

The Windows deployment directory also includes verified release staging and isolated installation-rehearsal tools. The package excludes tests, Python caches, development settings, fallback `appsettings.json`, PDB files, local environments, certificates, keys, and release-building tools. Production env files are never packaged and must remain in the protected external configuration directory.

## Validation

Validate a package again before copying or extracting it:

```powershell
cd C:\path\to\mes-v1\backend
.\.venv\Scripts\python.exe -m scripts.release_package validate `
  --package E:\MES\release-packages\mes-v2-01234567.zip `
  --expected-commit 0123456789abcdef0123456789abcdef01234567
```

Validation rejects unsafe ZIP paths, duplicate entries, excessive expansion, missing runtime files, unlisted files, hash or size differences, wheelhouse/requirements mismatches, development settings, caches, private-key or credential files, high-confidence secret patterns, insecure WPF Production URLs, and a different commit.

The quality-evidence hash covers the report commit, overall decision, clean-worktree and restore options, and each check name, status, and summary. Volatile run time, duration, and log paths are deliberately excluded so they cannot change package identity.

ZIP entries are sorted and use the Git commit time. Combined with deterministic .NET builds and commit-derived metadata, rebuilding the same commit from the same branch with the same SDK produces the same package bytes. Retain the SDK version, original release-validation report, package manifest, and package SHA-256 in the release record.

## Installation Boundary

Install the approved ZIP with `Install-MesRelease.ps1`; do not manually extract over the running release. Run the isolated file-switch and recovery rehearsal documented in `docs/release-installation-rehearsal.md`, then run the offline Python and API-startup rehearsal documented in `docs/runtime-rehearsal.md`. Protected production env-file connection, ACL application, service switching, migration approval, production smoke testing, and rollback remain separate deployment steps documented in `docs/operations-monitoring-deployment.md`.
