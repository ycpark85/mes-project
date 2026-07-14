from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Mapping, Sequence
from urllib.parse import parse_qs, unquote, urlsplit

import psycopg
from dotenv import dotenv_values
from psycopg import sql


BACKUP_FORMAT_VERSION = 1
RESTORE_DATABASE_PATTERN = re.compile(r"^mes_restore_test_[a-z0-9_]{1,40}$")
STORAGE_ENV_KEYS = (
    "DRAWING_STORAGE_ROOT",
    "DEFECT_PHOTO_STORAGE_ROOT",
    "PLATE_DATA_STORAGE_ROOT",
)
ADMIN_DATABASE_URL_ENV_KEY = "MES_BACKUP_ADMIN_DATABASE_URL"


@dataclass(frozen=True)
class PostgresConnectionInfo:
    host: str
    port: int
    username: str
    password: str | None
    database: str
    sslmode: str | None = None

    def tool_args(self, database: str | None = None) -> list[str]:
        return [
            "--host",
            self.host,
            "--port",
            str(self.port),
            "--username",
            self.username,
            "--dbname",
            database or self.database,
        ]

    def child_environment(self) -> dict[str, str]:
        environment = os.environ.copy()
        if self.password is not None:
            environment["PGPASSWORD"] = self.password
        if self.sslmode:
            environment["PGSSLMODE"] = self.sslmode
        return environment

    def connect_kwargs(self, database: str | None = None) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "host": self.host,
            "port": self.port,
            "user": self.username,
            "dbname": database or self.database,
        }
        if self.password is not None:
            kwargs["password"] = self.password
        if self.sslmode:
            kwargs["sslmode"] = self.sslmode
        return kwargs


def load_runtime_values(env_file: Path) -> dict[str, str]:
    values = {
        key: str(value)
        for key, value in dotenv_values(env_file).items()
        if value is not None
    }
    for key in ("DATABASE_URL", ADMIN_DATABASE_URL_ENV_KEY, *STORAGE_ENV_KEYS):
        environment_value = os.environ.get(key)
        if environment_value:
            values[key] = environment_value
    return values


def parse_postgres_url(database_url: str) -> PostgresConnectionInfo:
    parsed = urlsplit(database_url)
    scheme = parsed.scheme.split("+", 1)[0].lower()
    if scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL must use PostgreSQL")
    if not parsed.hostname or not parsed.username:
        raise ValueError("DATABASE_URL must include host and username")

    database = unquote(parsed.path.lstrip("/"))
    if not database:
        raise ValueError("DATABASE_URL must include a database name")

    query = parse_qs(parsed.query, keep_blank_values=False)
    unsupported_options = set(query) - {"sslmode"}
    if unsupported_options:
        names = ", ".join(sorted(unsupported_options))
        raise ValueError(f"Unsupported DATABASE_URL options: {names}")

    sslmode_values = query.get("sslmode", [])
    return PostgresConnectionInfo(
        host=parsed.hostname,
        port=parsed.port or 5432,
        username=unquote(parsed.username),
        password=unquote(parsed.password) if parsed.password is not None else None,
        database=database,
        sslmode=sslmode_values[0] if sslmode_values else None,
    )


def resolve_postgres_tool(name: str, pg_bin: Path | None = None) -> Path:
    executable_name = f"{name}.exe" if os.name == "nt" else name
    if pg_bin is not None:
        candidate = (pg_bin / executable_name).resolve()
        if candidate.is_file():
            return candidate
        raise FileNotFoundError(f"PostgreSQL tool not found: {candidate}")

    resolved = shutil.which(name)
    if not resolved:
        raise FileNotFoundError(f"PostgreSQL tool is not on PATH: {name}")
    return Path(resolved).resolve()


def run_postgres_tool(
    arguments: Sequence[str | Path],
    connection: PostgresConnectionInfo,
    *,
    discard_stdout: bool = False,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        [str(argument) for argument in arguments],
        env=connection.child_environment(),
        stdout=subprocess.DEVNULL if discard_stdout else subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        tool_name = Path(str(arguments[0])).name
        detail = (process.stderr or "").strip()[-2000:]
        raise RuntimeError(
            f"{tool_name} failed with exit code {process.returncode}: {detail}"
        )
    return process


def tool_version(tool: Path) -> str:
    process = subprocess.run(
        [str(tool), "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(f"Failed to read tool version: {tool.name}")
    return process.stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_link(path: Path) -> bool:
    return path.is_symlink() or (
        hasattr(path, "is_junction") and path.is_junction()
    )


def copy_storage_root(source: Path, destination: Path) -> dict[str, object]:
    source = source.resolve(strict=True)
    if not source.is_dir():
        raise ValueError(f"Storage root is not a directory: {source}")
    if _is_link(source):
        raise ValueError(f"Storage root cannot be a link or junction: {source}")
    if destination.exists():
        raise FileExistsError(f"Storage backup destination already exists: {destination}")

    destination.mkdir(parents=True)
    records: list[dict[str, object]] = []
    total_bytes = 0

    for current_root, directory_names, file_names in os.walk(source):
        current = Path(current_root)
        directory_names.sort()
        file_names.sort()

        for directory_name in directory_names:
            source_directory = current / directory_name
            if _is_link(source_directory):
                raise ValueError(
                    f"Storage backup does not follow links or junctions: {source_directory}"
                )
            relative_directory = source_directory.relative_to(source)
            (destination / relative_directory).mkdir(parents=True, exist_ok=True)

        for file_name in file_names:
            source_file = current / file_name
            if _is_link(source_file):
                raise ValueError(
                    f"Storage backup does not follow linked files: {source_file}"
                )

            relative_file = source_file.relative_to(source)
            destination_file = destination / relative_file
            destination_file.parent.mkdir(parents=True, exist_ok=True)
            before = source_file.stat()
            digest = hashlib.sha256()

            with source_file.open("rb") as input_stream, destination_file.open("xb") as output_stream:
                for chunk in iter(lambda: input_stream.read(1024 * 1024), b""):
                    output_stream.write(chunk)
                    digest.update(chunk)

            after = source_file.stat()
            if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
                raise RuntimeError(f"Storage file changed during backup: {source_file}")

            shutil.copystat(source_file, destination_file)
            total_bytes += before.st_size
            records.append(
                {
                    "path": relative_file.as_posix(),
                    "bytes": before.st_size,
                    "sha256": digest.hexdigest(),
                }
            )

    return {
        "file_count": len(records),
        "total_bytes": total_bytes,
        "files": records,
    }


def verify_file_records(base_directory: Path, records: Sequence[Mapping[str, object]]) -> None:
    base_directory = base_directory.resolve(strict=True)
    expected_paths: set[str] = set()

    for record in records:
        relative_path = str(record["path"])
        candidate = safe_child_path(base_directory, relative_path)
        if not candidate.is_file() or _is_link(candidate):
            raise RuntimeError(f"Backup file is missing or unsafe: {relative_path}")
        if candidate.stat().st_size != int(record["bytes"]):
            raise RuntimeError(f"Backup file size mismatch: {relative_path}")
        if sha256_file(candidate) != str(record["sha256"]):
            raise RuntimeError(f"Backup file hash mismatch: {relative_path}")
        expected_paths.add(Path(relative_path).as_posix())

    actual_paths = {
        path.relative_to(base_directory).as_posix()
        for path in base_directory.rglob("*")
        if path.is_file()
    }
    if actual_paths != expected_paths:
        raise RuntimeError("Backup storage file list does not match its manifest")


def safe_child_path(parent: Path, relative_path: str) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe relative path in backup manifest: {relative_path}")
    parent = parent.resolve()
    candidate = (parent / relative).resolve()
    if not candidate.is_relative_to(parent):
        raise ValueError(f"Backup manifest path escapes its root: {relative_path}")
    return candidate


def collect_storage_roots(
    values: Mapping[str, str],
    labels: Sequence[str] = STORAGE_ENV_KEYS,
) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for label in labels:
        raw_path = values.get(label, "").strip()
        if not raw_path:
            continue
        resolved = Path(raw_path).resolve(strict=True)
        key = os.path.normcase(str(resolved))
        if key not in grouped:
            grouped[key] = {"source": resolved, "labels": []}
        grouped[key]["labels"].append(label)
    if not grouped:
        raise ValueError("No file storage roots are configured")
    return list(grouped.values())


def ensure_backup_path_is_separate(
    backup_root: Path,
    storage_roots: Sequence[Path],
) -> None:
    backup_root = backup_root.resolve()
    for source in storage_roots:
        source = source.resolve(strict=True)
        if (
            backup_root == source
            or backup_root.is_relative_to(source)
            or source.is_relative_to(backup_root)
        ):
            raise ValueError(
                f"Backup root and storage root must not contain each other: "
                f"{backup_root} / {source}"
            )


@contextmanager
def backup_lock(backup_root: Path) -> Iterator[None]:
    lock_path = backup_root / ".mes_backup.lock"
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(
            f"Another backup may be running. Remove a stale lock only after checking: {lock_path}"
        ) from exc

    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as lock_file:
            lock_file.write(str(os.getpid()))
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def database_snapshot(connection: PostgresConnectionInfo) -> dict[str, object]:
    with psycopg.connect(**connection.connect_kwargs()) as db:
        with db.cursor() as cursor:
            cursor.execute("SHOW server_version")
            server_version = cursor.fetchone()[0]
            cursor.execute("SHOW server_encoding")
            server_encoding = cursor.fetchone()[0]
            cursor.execute("SELECT to_regclass('public.alembic_version')")
            has_alembic = cursor.fetchone()[0] is not None
            alembic_version = None
            if has_alembic:
                cursor.execute("SELECT version_num FROM alembic_version")
                row = cursor.fetchone()
                alembic_version = row[0] if row else None
            cursor.execute(
                "SELECT count(*) FROM pg_catalog.pg_tables WHERE schemaname = 'public'"
            )
            public_table_count = cursor.fetchone()[0]

    return {
        "name": connection.database,
        "server_version": server_version,
        "server_encoding": server_encoding,
        "alembic_version": alembic_version,
        "public_table_count": public_table_count,
    }


def validate_restore_database_name(target: str, source: str) -> None:
    if target == source:
        raise ValueError("Restore target must not be the source database")
    if not RESTORE_DATABASE_PATTERN.fullmatch(target):
        raise ValueError(
            "Restore target must match mes_restore_test_[a-z0-9_]+"
        )


def database_exists(connection: PostgresConnectionInfo, database: str) -> bool:
    with psycopg.connect(**connection.connect_kwargs("postgres")) as admin:
        with admin.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
            return cursor.fetchone() is not None


def create_restore_database(
    admin_connection: PostgresConnectionInfo,
    database: str,
    *,
    source_database: str,
    owner: str,
) -> None:
    validate_restore_database_name(database, source_database)
    if database_exists(admin_connection, database):
        raise RuntimeError(f"Restore target already exists: {database}")

    admin = psycopg.connect(**admin_connection.connect_kwargs("postgres"))
    try:
        admin.autocommit = True
        with admin.cursor() as cursor:
            try:
                cursor.execute(
                    sql.SQL(
                        "CREATE DATABASE {} WITH TEMPLATE template0 OWNER {}"
                    ).format(
                        sql.Identifier(database),
                        sql.Identifier(owner),
                    )
                )
            except psycopg.errors.InsufficientPrivilege as exc:
                raise RuntimeError(
                    "Restore verification requires a separate CREATEDB role. "
                    f"Set {ADMIN_DATABASE_URL_ENV_KEY} for the restore process."
                ) from exc
    finally:
        admin.close()


def drop_restore_database(
    admin_connection: PostgresConnectionInfo,
    database: str,
    *,
    source_database: str,
) -> None:
    validate_restore_database_name(database, source_database)
    admin = psycopg.connect(**admin_connection.connect_kwargs("postgres"))
    try:
        admin.autocommit = True
        with admin.cursor() as cursor:
            cursor.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (database,),
            )
            cursor.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database))
            )
    finally:
        admin.close()


def load_manifest(backup_directory: Path) -> dict[str, object]:
    manifest_path = backup_directory / "manifest.json"
    with manifest_path.open("r", encoding="utf-8") as manifest_file:
        manifest = json.load(manifest_file)
    if manifest.get("format_version") != BACKUP_FORMAT_VERSION:
        raise ValueError("Unsupported MES backup format version")
    return manifest


def write_manifest(path: Path, manifest: Mapping[str, object]) -> None:
    temporary_path = path.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(path)


def remove_generated_directory(path: Path, parent: Path, prefix: str) -> None:
    parent = parent.resolve()
    path = path.resolve()
    if path.parent != parent or not path.name.startswith(prefix):
        raise ValueError(f"Refusing to remove an unverified generated directory: {path}")
    if path.exists():
        shutil.rmtree(path)
