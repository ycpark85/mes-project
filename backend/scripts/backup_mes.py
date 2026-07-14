from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.mes_backup_common import (
    BACKUP_FORMAT_VERSION,
    backup_lock,
    collect_storage_roots,
    copy_storage_root,
    database_snapshot,
    ensure_backup_path_is_separate,
    load_runtime_values,
    parse_postgres_url,
    remove_generated_directory,
    resolve_postgres_tool,
    run_postgres_tool,
    sha256_file,
    tool_version,
    write_manifest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a verified MES PostgreSQL and file-storage backup."
    )
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=BACKEND_ROOT / ".env",
    )
    parser.add_argument("--pg-bin", type=Path)
    parser.add_argument(
        "--storage-root",
        type=Path,
        action="append",
        help=(
            "File storage root to back up. Repeat for multiple distinct roots. "
            "Overrides storage paths from the env file."
        ),
    )
    parser.add_argument(
        "--consistency-mode",
        choices=("maintenance", "online"),
        required=True,
        help=(
            "Use maintenance only after write traffic is stopped. Online records "
            "that the DB and file copy are not one atomic snapshot."
        ),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    values = load_runtime_values(args.env_file)
    database_url = values.get("DATABASE_URL", "").strip()
    if not database_url:
        raise ValueError("DATABASE_URL is missing")

    connection = parse_postgres_url(database_url)
    if args.storage_root:
        explicit_roots = {
            f"CLI_STORAGE_ROOT_{index}": str(path)
            for index, path in enumerate(args.storage_root, start=1)
        }
        storage_roots = collect_storage_roots(
            explicit_roots,
            tuple(explicit_roots),
        )
    else:
        storage_roots = collect_storage_roots(values)
    backup_root = args.backup_root.resolve()
    backup_root.mkdir(parents=True, exist_ok=True)
    ensure_backup_path_is_separate(
        backup_root,
        [item["source"] for item in storage_roots],
    )

    pg_dump = resolve_postgres_tool("pg_dump", args.pg_bin)
    pg_restore = resolve_postgres_tool("pg_restore", args.pg_bin)
    created_at = datetime.now(UTC)
    backup_id = created_at.strftime("mes_%Y%m%dT%H%M%SZ")
    final_directory = backup_root / backup_id
    incomplete_directory = backup_root / f".{backup_id}.incomplete"

    if final_directory.exists() or incomplete_directory.exists():
        raise FileExistsError(f"Backup id already exists: {backup_id}")

    with backup_lock(backup_root):
        incomplete_directory.mkdir()
        try:
            database_metadata = database_snapshot(connection)
            dump_path = incomplete_directory / "database.dump"
            run_postgres_tool(
                [
                    pg_dump,
                    *connection.tool_args(),
                    "--format=custom",
                    "--compress=6",
                    "--no-owner",
                    "--no-privileges",
                    "--file",
                    dump_path,
                ],
                connection,
            )
            run_postgres_tool(
                [pg_restore, "--list", dump_path],
                connection,
                discard_stdout=True,
            )

            storage_manifests: list[dict[str, object]] = []
            for index, item in enumerate(storage_roots, start=1):
                storage_id = f"storage_{index:02d}"
                relative_backup_path = Path("files") / storage_id
                copy_result = copy_storage_root(
                    item["source"],
                    incomplete_directory / relative_backup_path,
                )
                storage_manifests.append(
                    {
                        "id": storage_id,
                        "labels": item["labels"],
                        "source_path": str(item["source"]),
                        "backup_path": relative_backup_path.as_posix(),
                        **copy_result,
                    }
                )

            manifest = {
                "format_version": BACKUP_FORMAT_VERSION,
                "backup_id": backup_id,
                "created_at_utc": created_at.isoformat(),
                "consistency_mode": args.consistency_mode,
                "database": {
                    **database_metadata,
                    "dump_file": "database.dump",
                    "dump_bytes": dump_path.stat().st_size,
                    "dump_sha256": sha256_file(dump_path),
                    "pg_dump_version": tool_version(pg_dump),
                    "pg_restore_version": tool_version(pg_restore),
                },
                "storage_sets": storage_manifests,
            }
            write_manifest(incomplete_directory / "manifest.json", manifest)
            incomplete_directory.replace(final_directory)
        except BaseException:
            remove_generated_directory(
                incomplete_directory,
                backup_root,
                ".mes_",
            )
            raise

    database_dump_bytes = final_directory.joinpath("database.dump").stat().st_size
    storage_bytes = sum(
        int(item["total_bytes"])
        for item in storage_manifests
    )
    print(f"backup_created={final_directory}")
    print(f"database_dump_bytes={database_dump_bytes}")
    print(f"storage_bytes={storage_bytes}")
    print(f"consistency_mode={args.consistency_mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
