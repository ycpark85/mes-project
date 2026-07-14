# MES Operations Monitoring And Windows Deployment

## Scope

These tools prepare a staged MES V2 release for Windows operation. They do not copy release binaries, publish WPF clients, configure a reverse proxy, or decide the production server paths. Stage and review the release first, then run the deployment gate from that fixed revision.

The operational tools are:

- `backend/scripts/check_mes_operations.py`: read-only database, disk, backup, and restore-age checks.
- `backend/scripts/configure_postgres_monitoring.py`: explicit PostgreSQL monitoring preparation.
- `deploy/windows/Test-MesDeployment.ps1`: read-only production preflight.
- `deploy/windows/Invoke-MesDeployment.ps1`: maintenance backup, approved PostgreSQL setup, migration, task registration, and smoke-test orchestration.
- `deploy/windows/Set-MesOperationsScheduledTasks.ps1`: idempotent task registration or removal.
- `deploy/windows/Invoke-MesScheduledOperation.ps1`: scheduled backup and monitoring runner with file logs.

The FastAPI startup path never creates roles, changes PostgreSQL settings, restarts services, runs Alembic upgrades, or deletes backups.

## Required Configuration

Copy `deploy/windows/mes-deployment.example.psd1` outside the release directory and replace every example path and service name. The deployment config contains paths, times, and service names only. Never put a password, database URL, token, or API key in it.

Use two protected env files:

1. The backend env file contains the production application settings. `APP_ENV` must be `prod` or `production`; all three storage roots must be explicit.
2. The monitor env file contains only `MES_MONITOR_DATABASE_URL` or `DATABASE_URL` for a login role named `mes_monitor` or `mes_monitor_*`.

Restrict both env files to the relevant Windows service accounts and administrators. Do not put the monitor URL in the backend env file because application settings reject unknown keys and the API does not need monitoring credentials.

The preflight rejects broad write access for the staged backend, deployment scripts, deployment config, and env files. It also rejects broad read access for both env files. This is required because a scheduled task may run as SYSTEM; an ordinary user who can modify a task script/config or read a database credential would otherwise gain excessive access.

The PostgreSQL administrator URL is never stored in the deployment config. Supply it only to the elevated deployment process:

```powershell
$env:MES_BACKUP_ADMIN_DATABASE_URL = 'postgresql://deployment_admin@127.0.0.1:5432/postgres'
```

Use a protected PostgreSQL password file where possible. Remove the process variable when the deployment ends.

## Read-Only Operations Check

```powershell
cd C:\MES\v2\backend
.\.venv\Scripts\python.exe -m scripts.check_mes_operations `
  --env-file C:\MES\config\backend.env `
  --monitor-env-file C:\MES\config\monitor.env `
  --backup-root E:\MES\backups `
  --restore-record E:\MES\monitoring\last-restore.json `
  --history-root E:\MES\monitoring\history
```

Exit codes:

- `0`: normal.
- `1`: warning; review but deployment may continue when the warning is understood.
- `2`: critical or execution failure.

Default thresholds:

| Check | Warning | Critical |
|---|---:|---:|
| PostgreSQL connections | 60% | 80% |
| Free disk space | 20% | 10% |
| Lock wait | 5 seconds | 30 seconds |
| Active query | 30 seconds | 150 seconds |
| Idle transaction | 30 seconds | 60 seconds |
| Latest backup age | 26 hours | 48 hours |
| Restore rehearsal age | 90 days | 120 days |
| Dead tuples | 10,000 and 20% | 100,000 and 40% |

Any invalid or incomplete index is critical. Cumulative deadlocks are a warning. A populated table with no planner statistics is a warning and should be analyzed in a maintenance window.

The DB transaction is read-only and has a 10-second statement timeout. Output contains no SQL text, SQL parameters, URLs, or passwords. History JSON contains only operational metrics.

## PostgreSQL Monitoring Setup

The deployment administrator and monitor URLs must point to the same PostgreSQL server. The monitor URL must target the application database and must use a separate role.

`prepare --apply` performs only these idempotent actions:

1. Create the declared monitor login when it does not exist, using a client-generated SCRAM verifier.
2. Grant `pg_monitor` and database `CONNECT`.
3. Preserve existing `shared_preload_libraries` entries and append `pg_stat_statements` when missing.

If the preload setting changes, the tool returns exit code `3`. PostgreSQL must be restarted in the approved maintenance window. After restart, `finalize --apply` creates the extension and verifies an actual monitor-role connection. Re-running either phase does not duplicate the role, grant, library entry, or extension.

The deployment script performs the restart only when both `-ApplyPostgresMonitoring` and `-ApprovePostgresRestart` are supplied.
The generated monitor password must use printable ASCII characters so the client-generated PostgreSQL SCRAM verifier is deterministic and portable.

## Deployment Gate

First run the read-only gate:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File C:\MES\v2\deploy\windows\Invoke-MesDeployment.ps1 `
  -ConfigFile C:\MES\config\mes-deployment.psd1
```

With no apply switches, no server state changes. The gate validates production settings, storage separation, PostgreSQL tools, Alembic current/heads, the latest backup, restore rehearsal age, disk capacity, and database health. A warning blocks apply steps unless the operator reviews it and supplies `-ApproveWarnings`.

After staging and reviewing the release, an elevated maintenance-window activation can use:

```powershell
$env:MES_BACKUP_ADMIN_DATABASE_URL = 'postgresql://deployment_admin@127.0.0.1:5432/postgres'

powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File C:\MES\v2\deploy\windows\Invoke-MesDeployment.ps1 `
  -ConfigFile C:\MES\config\mes-deployment.psd1 `
  -ApplyPostgresMonitoring `
  -ApprovePostgresRestart `
  -ApproveWarnings `
  -ApplyMigration `
  -RegisterOperationsTasks `
  -RunSmokeTest

Remove-Item Env:\MES_BACKUP_ADMIN_DATABASE_URL
```

The activation sequence is:

1. Run the read-only preflight.
2. Stop the configured API Windows service.
3. Refuse to continue if an unmanaged API process still answers the health endpoint.
4. Create a verified maintenance-mode DB and file backup.
5. Apply approved PostgreSQL monitoring setup and restart only when required.
6. Review Alembic current/heads, run `alembic upgrade head`, then require `current --check-heads` and `alembic check` against the upgraded schema.
7. Register or update scheduled tasks.
8. Restart the API service in a `finally` path.
9. Run health and readiness smoke tests when requested.

An Alembic upgrade is never run without `-ApplyMigration`. PostgreSQL is never restarted without `-ApprovePostgresRestart`.

## Scheduled Tasks

The registration script creates or updates these tasks under `\MES\`:

- `MES Daily Verified Backup`: online DB and file backup at the configured backup time.
- `MES Daily Operations Check`: read-only monitoring and history output at the configured monitor time.

Online daily backup keeps the PostgreSQL dump transaction-consistent, but files may represent a slightly different instant when users are writing. Deployment and quarterly baselines must use maintenance mode with API write traffic stopped.

The task principal defaults to `NT AUTHORITY\SYSTEM` only for local disks. The script rejects SYSTEM with a UNC backup path. For NAS or network storage, configure a dedicated service account or gMSA with only the required read/write permissions.

Task registration is idempotent. Remove both tasks without touching backup data or history:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File C:\MES\v2\deploy\windows\Set-MesOperationsScheduledTasks.ps1 `
  -ConfigFile C:\MES\config\mes-deployment.psd1 `
  -Mode Unregister
```

No backup-retention deletion is performed. Configure retention in the approved backup platform after the production destination and policy are confirmed.

## Failure And Recovery

- Preflight critical: do not apply. Correct the reported path, backup, restore, disk, DB, or migration issue and rerun.
- Monitoring prepare returns `3` without restart approval: the configuration is written but not active. The API remains stopped; rerun with restart approval in the maintenance window or review and restart the original API service manually.
- PostgreSQL restart or finalize fails: do not migrate. Review PostgreSQL logs and restore the previous preload setting if necessary.
- Migration or monitoring maintenance fails: the API service remains stopped and the database is not automatically downgraded. Review the exact completed step, PostgreSQL/Alembic state, and the verified pre-deployment backup before manually restarting or recovering.
- Scheduled task fails: inspect the timestamped operation log and Task Scheduler result. Do not expose env-file contents in support messages.
- Smoke test fails: keep the release under investigation and verify readiness, database revision, application logs, file permissions, and the request ID before allowing normal use.

Record every production deployment revision, backup ID, Alembic revision, operator, start/end time, warnings, and rollback decision in the operating log.
