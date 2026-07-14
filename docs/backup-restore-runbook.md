# MES Backup And Restore Runbook

## Scope

An MES backup is complete only when it contains both of these parts:

- PostgreSQL custom-format dump created by `pg_dump`.
- Every configured file storage root used for drawings, defect photos, and plate data.

The backup tools are:

- `backend/scripts/backup_mes.py`
- `backend/scripts/verify_mes_restore.py`
- `backend/scripts/check_mes_operations.py`

They do not store database passwords in command arguments, the manifest, or logs. The application `DATABASE_URL` is read from the selected env file or process environment, and the password is passed to PostgreSQL tools only through the child-process environment.

## Safety Rules

- The backup destination and each storage root must not contain each other. This prevents recursive self-backup and accidental source deletion.
- Storage links and directory junctions are rejected. The tool never follows a path outside the declared storage root.
- Each copied file records size and SHA-256. A source file that changes during copy fails the backup.
- A backup is first written to a `.incomplete` directory and renamed only after `pg_restore --list`, hashes, file copies, and manifest writing succeed.
- Restore database names must match `mes_restore_test_[a-z0-9_]+` and must differ from the source database name.
- The restore tool never overwrites an existing database.
- Without `--keep-restored-artifacts`, the generated test database and restored files are removed after success or failure.
- Do not put backup output under Git or under an MES file storage root.

## Create A Backup

Stop MES write traffic before using maintenance mode. The tool records the selected mode but does not stop the API service itself.

```powershell
cd C:\path\to\mes-v1\backend
.\.venv\Scripts\python.exe -m scripts.backup_mes `
  --backup-root E:\mes_backups `
  --consistency-mode maintenance
```

If storage paths are not explicitly present in the selected env file, pass the effective application path. Repeat the option only for distinct roots; duplicate resolved paths are backed up once.

```powershell
.\.venv\Scripts\python.exe -m scripts.backup_mes `
  --backup-root E:\mes_backups `
  --storage-root C:\mes_storage `
  --consistency-mode maintenance
```

`online` mode is available when write traffic cannot be stopped, but it is not a fully atomic DB-and-file snapshot. PostgreSQL remains transaction-consistent; the file tree may represent a slightly different instant. Maintenance mode is the required mode for deployment and quarterly restore baselines.

Each completed backup directory contains:

- `database.dump`
- `files/storage_XX/...`
- `manifest.json`

The manifest records dump hash, PostgreSQL tool versions, Alembic version, public table count, deduplicated storage labels, and file hashes. It contains no password.

## Restore Verification

The normal application role should not have `CREATEDB`. Use a separate restore operator only while running the drill.

The restore operator needs:

- `CREATEDB`.
- Membership in the application DB role so it can create a temporary database owned by that role.
- No application login or routine API usage.

Provide its connection through the process environment, not `backend/.env`. Prefer a protected PostgreSQL password file so the URL does not contain a password.

```powershell
$env:MES_BACKUP_ADMIN_DATABASE_URL = 'postgresql://mes_restore_operator@127.0.0.1:5432/postgres'

.\.venv\Scripts\python.exe -m scripts.verify_mes_restore `
  --backup-dir E:\mes_backups\mes_YYYYMMDDTHHMMSSZ `
  --work-root E:\mes_restore_work `
  --record-file E:\mes_monitoring\last-restore.json

Remove-Item Env:\MES_BACKUP_ADMIN_DATABASE_URL
```

The verification performs these checks:

1. Manifest format and safe paths.
2. Dump size, SHA-256, and `pg_restore --list` readability.
3. Every backed-up file size and SHA-256.
4. New isolated restore DB creation.
5. `pg_restore --exit-on-error` into the isolated DB.
6. Server encoding, Alembic revision, and public table count comparison.
7. File copy into a separate restore directory and a second hash comparison.
8. Test DB and restored-file cleanup.
9. Atomic restore-success record writing after cleanup when `--record-file` is supplied.

If cleanup is intentionally disabled with `--keep-restored-artifacts`, the operator is responsible for deleting only the generated test DB and restore directory after inspection.

## Scheduling And Retention

Production task registration is provided by `deploy/windows/Set-MesOperationsScheduledTasks.ps1`. Do not register it until the server service account, backup destination, monitor history path, and alert-review process are confirmed. The deployment and monitoring details are in `docs/operations-monitoring-deployment.md`.

Recommended baseline:

- Daily backups: retain 14.
- Weekly backups: retain 8.
- Monthly backups: retain at least 12.
- Quarterly: restore one selected backup into an isolated DB and record the result.

Automatic retention deletion is intentionally not implemented in the script. Use the approved backup platform or a separately reviewed cleanup task constrained to the dedicated backup root.

Follow the 3-2-1 rule:

- Three copies of important data.
- Two different storage media or systems.
- One copy outside the MES server.

A backup on another folder of the same disk is a restore test artifact, not disaster recovery.

## Source Code Protection

Local Git commits protect against accidental edits but not disk failure. The preferred protection is a private remote branch after confirming that repository-level external deployment hooks are absent or disabled.

When the V2 branch must remain unpushed, create and verify a Git bundle, then copy it to another machine or encrypted removable storage:

```powershell
git bundle create E:\mes_backups\mes-v2-source.bundle security/deploy-prep
git bundle verify E:\mes_backups\mes-v2-source.bundle
```

Do not store `.env`, PostgreSQL password files, DB dumps, or file-storage backups in the Git repository.

## Verified Local Drill

On 2026-07-14, local verification used PostgreSQL 17.10 and backup `mes_20260714T012236Z`.

- Source DB dump size: 372,792 bytes.
- File storage size: 1,098,013 bytes.
- Restored public tables: 51.
- Restored Alembic revision: `29d3e4f5a6b7`.
- Restored storage sets: 1 because the three application storage settings resolved to the same local root.
- The drill ran in a disposable PostgreSQL 17 cluster. The test DB, restored files, cluster, log, and port were removed or closed afterward.
- The retained backup is under `C:\mes_backups\local-validation`; it is on the same disk and must not be treated as the required off-machine copy.
