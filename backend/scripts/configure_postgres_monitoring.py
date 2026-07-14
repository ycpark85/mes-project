from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import os
import re
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg import sql


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.mes_backup_common import (
    ADMIN_DATABASE_URL_ENV_KEY,
    PostgresConnectionInfo,
    load_runtime_values,
    parse_postgres_url,
)


MONITOR_DATABASE_URL_KEY = "MES_MONITOR_DATABASE_URL"
MONITOR_ROLE_PATTERN = re.compile(r"^mes_monitor(?:_[a-z0-9_]{1,32})?$")
RESTART_REQUIRED_EXIT_CODE = 3


@dataclass(frozen=True)
class MonitoringState:
    monitor_role_exists: bool
    monitor_role_granted: bool
    pg_stat_statements_preloaded: bool
    pg_stat_statements_installed: bool


def _load_monitor_url(monitor_env_file: Path | None) -> str:
    process_value = os.environ.get(MONITOR_DATABASE_URL_KEY, "").strip()
    if process_value:
        return process_value
    if monitor_env_file is None:
        raise ValueError(
            f"Set {MONITOR_DATABASE_URL_KEY} or provide --monitor-env-file"
        )
    values = dotenv_values(monitor_env_file)
    value = str(
        values.get(MONITOR_DATABASE_URL_KEY)
        or values.get("DATABASE_URL")
        or ""
    ).strip()
    if not value:
        raise ValueError(
            "Monitor env file must contain MES_MONITOR_DATABASE_URL or DATABASE_URL"
        )
    return value


def _validate_connections(
    application: PostgresConnectionInfo,
    administrator: PostgresConnectionInfo,
    monitor: PostgresConnectionInfo,
) -> None:
    endpoints = {
        (application.host.lower(), application.port),
        (administrator.host.lower(), administrator.port),
        (monitor.host.lower(), monitor.port),
    }
    if len(endpoints) != 1:
        raise ValueError(
            "Application, administrator, and monitor URLs must use the same PostgreSQL server"
        )
    if monitor.database != application.database:
        raise ValueError("Monitor URL must target the application database")
    if not MONITOR_ROLE_PATTERN.fullmatch(monitor.username):
        raise ValueError(
            "Monitor role must be mes_monitor or start with mes_monitor_"
        )
    if monitor.username in {application.username, administrator.username}:
        raise ValueError("Monitor role must be separate from application and administrator roles")


def _preload_items(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _with_pg_stat_statements(value: str) -> tuple[str, bool]:
    items = _preload_items(value)
    if "pg_stat_statements" in items:
        return ",".join(items), False
    items.append("pg_stat_statements")
    return ",".join(items), True


def build_scram_verifier(
    password: str,
    *,
    salt: bytes | None = None,
    iterations: int = 4096,
) -> str:
    if not password:
        raise ValueError("Monitor role password is required when creating the role")
    try:
        password_bytes = password.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(
            "Monitor role password must use printable ASCII characters"
        ) from exc
    if iterations < 4096:
        raise ValueError("SCRAM iteration count must be at least 4096")
    salt = salt or secrets.token_bytes(16)
    salted_password = hashlib.pbkdf2_hmac(
        "sha256",
        password_bytes,
        salt,
        iterations,
    )
    client_key = hmac.new(salted_password, b"Client Key", hashlib.sha256).digest()
    stored_key = hashlib.sha256(client_key).digest()
    server_key = hmac.new(salted_password, b"Server Key", hashlib.sha256).digest()
    return (
        f"SCRAM-SHA-256${iterations}:"
        f"{base64.b64encode(salt).decode('ascii')}$"
        f"{base64.b64encode(stored_key).decode('ascii')}:"
        f"{base64.b64encode(server_key).decode('ascii')}"
    )


def _connect(
    connection: PostgresConnectionInfo,
    database: str,
) -> psycopg.Connection:
    kwargs = connection.connect_kwargs(database)
    kwargs.update(
        connect_timeout=5,
        application_name="mes-monitoring-setup",
    )
    return psycopg.connect(**kwargs)


def _inspect_state(
    administrator: PostgresConnectionInfo,
    database: str,
    monitor_role: str,
) -> MonitoringState:
    with _connect(administrator, database) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SHOW shared_preload_libraries")
            preload = str(cursor.fetchone()[0])
            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = %s)",
                ("pg_stat_statements",),
            )
            extension_installed = bool(cursor.fetchone()[0])
            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = %s)",
                (monitor_role,),
            )
            role_exists = bool(cursor.fetchone()[0])
            role_granted = False
            if role_exists:
                cursor.execute(
                    "SELECT pg_has_role(%s, 'pg_monitor', 'MEMBER')",
                    (monitor_role,),
                )
                role_granted = bool(cursor.fetchone()[0])

    return MonitoringState(
        monitor_role_exists=role_exists,
        monitor_role_granted=role_granted,
        pg_stat_statements_preloaded=(
            "pg_stat_statements" in _preload_items(preload)
        ),
        pg_stat_statements_installed=extension_installed,
    )


def _ensure_monitor_role(
    cursor: psycopg.Cursor,
    monitor: PostgresConnectionInfo,
) -> bool:
    cursor.execute(
        """
        SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
               rolreplication, rolbypassrls
        FROM pg_roles
        WHERE rolname = %s
        """,
        (monitor.username,),
    )
    role = cursor.fetchone()
    exists = role is not None
    if not exists:
        if monitor.password is None:
            raise ValueError(
                "Monitor URL must include a password when the monitor role does not exist"
            )
        verifier = build_scram_verifier(monitor.password)
        cursor.execute(
            sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                sql.Identifier(monitor.username),
                sql.Literal(verifier),
            )
        )
    else:
        if not bool(role[0]):
            raise RuntimeError("Existing monitor role cannot log in")
        if any(bool(value) for value in role[1:]):
            raise RuntimeError("Existing monitor role has excessive PostgreSQL privileges")
    cursor.execute(
        sql.SQL("GRANT pg_monitor TO {}").format(
            sql.Identifier(monitor.username)
        )
    )
    cursor.execute(
        sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
            sql.Identifier(monitor.database),
            sql.Identifier(monitor.username),
        )
    )
    return not exists


def _prepare(
    administrator: PostgresConnectionInfo,
    monitor: PostgresConnectionInfo,
) -> bool:
    connection = _connect(administrator, monitor.database)
    try:
        connection.autocommit = True
        with connection.cursor() as cursor:
            created = _ensure_monitor_role(cursor, monitor)
            cursor.execute("SHOW shared_preload_libraries")
            current_preload = str(cursor.fetchone()[0])
            updated_preload, restart_required = _with_pg_stat_statements(
                current_preload
            )
            if restart_required:
                cursor.execute(
                    sql.SQL("ALTER SYSTEM SET shared_preload_libraries = {}").format(
                        sql.Literal(updated_preload)
                    )
                )
    finally:
        connection.close()

    print(f"monitor_role_created={str(created).lower()}")
    print(f"restart_required={str(restart_required).lower()}")
    return restart_required


def _finalize(
    administrator: PostgresConnectionInfo,
    monitor: PostgresConnectionInfo,
) -> None:
    connection = _connect(administrator, monitor.database)
    try:
        connection.autocommit = True
        with connection.cursor() as cursor:
            _ensure_monitor_role(cursor, monitor)
            cursor.execute("SHOW shared_preload_libraries")
            preload = str(cursor.fetchone()[0])
            if "pg_stat_statements" not in _preload_items(preload):
                raise RuntimeError(
                    "pg_stat_statements is not preloaded; restart PostgreSQL after prepare"
                )
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
    finally:
        connection.close()

    with _connect(monitor, monitor.database) as monitor_connection:
        with monitor_connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            cursor.execute(
                "SELECT pg_has_role(current_user, 'pg_monitor', 'MEMBER')"
            )
            if not bool(cursor.fetchone()[0]):
                raise RuntimeError("Monitor role connection does not have pg_monitor")
            cursor.execute("SELECT 1 FROM pg_stat_statements LIMIT 1")
    print("monitoring_setup=ready")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check or prepare PostgreSQL monitoring for MES deployment."
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=BACKEND_ROOT / ".env",
    )
    parser.add_argument("--monitor-env-file", type=Path)
    parser.add_argument(
        "--phase",
        choices=("check", "prepare", "finalize"),
        default="check",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Required for prepare and finalize phases.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    values = load_runtime_values(args.env_file)
    application_url = values.get("DATABASE_URL", "").strip()
    administrator_url = values.get(ADMIN_DATABASE_URL_ENV_KEY, "").strip()
    monitor_url = _load_monitor_url(args.monitor_env_file)
    if not application_url:
        raise ValueError("DATABASE_URL is missing")
    if not administrator_url:
        raise ValueError(
            f"Set {ADMIN_DATABASE_URL_ENV_KEY} in the deployment process environment"
        )

    application = parse_postgres_url(application_url)
    administrator = parse_postgres_url(administrator_url)
    monitor = parse_postgres_url(monitor_url)
    _validate_connections(application, administrator, monitor)

    if args.phase in {"prepare", "finalize"} and not args.apply:
        raise ValueError(f"--phase {args.phase} requires --apply")

    if args.phase == "check":
        state = _inspect_state(
            administrator,
            application.database,
            monitor.username,
        )
        print(f"monitor_role_exists={str(state.monitor_role_exists).lower()}")
        print(f"monitor_role_granted={str(state.monitor_role_granted).lower()}")
        print(
            "pg_stat_statements_preloaded="
            f"{str(state.pg_stat_statements_preloaded).lower()}"
        )
        print(
            "pg_stat_statements_installed="
            f"{str(state.pg_stat_statements_installed).lower()}"
        )
        return 0 if all(state.__dict__.values()) else 1

    if args.phase == "prepare":
        restart_required = _prepare(administrator, monitor)
        if restart_required:
            return RESTART_REQUIRED_EXIT_CODE
        _finalize(administrator, monitor)
        return 0

    _finalize(administrator, monitor)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(
            f"monitoring_setup_failed={type(exc).__name__}",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
