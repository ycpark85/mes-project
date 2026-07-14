from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.mes_backup_common import (
    ADMIN_DATABASE_URL_ENV_KEY,
    copy_storage_root,
    create_restore_database,
    database_snapshot,
    drop_restore_database,
    load_manifest,
    load_runtime_values,
    parse_postgres_url,
    remove_generated_directory,
    resolve_postgres_tool,
    run_postgres_tool,
    safe_child_path,
    sha256_file,
    validate_restore_database_name,
    verify_file_records,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Restore and verify an MES backup in an isolated test database."
    )
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=BACKEND_ROOT / ".env",
    )
    parser.add_argument("--pg-bin", type=Path)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--target-database")
    parser.add_argument("--keep-restored-artifacts", action="store_true")
    return parser


def _verify_database_snapshot(
    expected: dict[str, object],
    actual: dict[str, object],
) -> None:
    for key in ("server_encoding", "alembic_version", "public_table_count"):
        if actual.get(key) != expected.get(key):
            raise RuntimeError(
                f"Restored database metadata mismatch for {key}: "
                f"expected={expected.get(key)!r}, actual={actual.get(key)!r}"
            )


def main() -> int:
    args = build_parser().parse_args()
    backup_directory = args.backup_dir.resolve(strict=True)
    manifest = load_manifest(backup_directory)
    values = load_runtime_values(args.env_file)
    database_url = values.get("DATABASE_URL", "").strip()
    if not database_url:
        raise ValueError("DATABASE_URL is missing")

    connection = parse_postgres_url(database_url)
    admin_database_url = values.get(ADMIN_DATABASE_URL_ENV_KEY, "").strip()
    admin_connection = (
        parse_postgres_url(admin_database_url)
        if admin_database_url
        else connection
    )
    expected_database = manifest["database"]
    if expected_database["name"] != connection.database:
        raise RuntimeError(
            "Backup source database does not match the configured source database"
        )

    target_database = args.target_database or datetime.now(UTC).strftime(
        "mes_restore_test_%Y%m%d_%H%M%S"
    )
    validate_restore_database_name(target_database, connection.database)
    work_root = args.work_root.resolve()
    work_root.mkdir(parents=True, exist_ok=True)
    restore_directory = work_root / f"restore_{target_database}"
    if restore_directory.exists():
        raise FileExistsError(f"Restore work directory already exists: {restore_directory}")

    pg_restore = resolve_postgres_tool("pg_restore", args.pg_bin)
    dump_path = safe_child_path(
        backup_directory,
        str(expected_database["dump_file"]),
    )
    if dump_path.stat().st_size != int(expected_database["dump_bytes"]):
        raise RuntimeError("Database dump size does not match the manifest")
    if sha256_file(dump_path) != expected_database["dump_sha256"]:
        raise RuntimeError("Database dump hash does not match the manifest")
    run_postgres_tool(
        [pg_restore, "--list", dump_path],
        connection,
        discard_stdout=True,
    )

    for storage_set in manifest["storage_sets"]:
        backup_storage = safe_child_path(
            backup_directory,
            str(storage_set["backup_path"]),
        )
        verify_file_records(backup_storage, storage_set["files"])

    created_database = False
    restore_directory.mkdir()
    try:
        create_restore_database(
            admin_connection,
            target_database,
            source_database=connection.database,
            owner=connection.username,
        )
        created_database = True
        run_postgres_tool(
            [
                pg_restore,
                *connection.tool_args(target_database),
                "--exit-on-error",
                "--no-owner",
                "--no-privileges",
                dump_path,
            ],
            connection,
        )

        restored_connection = type(connection)(
            host=connection.host,
            port=connection.port,
            username=connection.username,
            password=connection.password,
            database=target_database,
            sslmode=connection.sslmode,
        )
        actual_database = database_snapshot(restored_connection)
        _verify_database_snapshot(expected_database, actual_database)

        for storage_set in manifest["storage_sets"]:
            source_storage = safe_child_path(
                backup_directory,
                str(storage_set["backup_path"]),
            )
            restored_storage = restore_directory / str(storage_set["id"])
            copied = copy_storage_root(source_storage, restored_storage)
            if copied["files"] != storage_set["files"]:
                raise RuntimeError(
                    f"Restored storage manifest mismatch: {storage_set['id']}"
                )
            verify_file_records(restored_storage, storage_set["files"])

        print(f"restore_verified={target_database}")
        print(f"backup_id={manifest['backup_id']}")
        print(f"public_table_count={actual_database['public_table_count']}")
        print(f"alembic_version={actual_database['alembic_version']}")
        print(f"storage_set_count={len(manifest['storage_sets'])}")
    finally:
        if not args.keep_restored_artifacts:
            try:
                if created_database:
                    drop_restore_database(
                        admin_connection,
                        target_database,
                        source_database=connection.database,
                    )
            finally:
                if restore_directory.exists():
                    remove_generated_directory(
                        restore_directory,
                        work_root,
                        "restore_mes_restore_test_",
                    )

    if args.keep_restored_artifacts:
        print(f"restored_files={restore_directory}")
    else:
        print("restored_test_artifacts_removed=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
