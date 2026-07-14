from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, Mapping

import psycopg
from dotenv import dotenv_values
from psycopg.rows import dict_row


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.mes_backup_common import (
    collect_storage_roots,
    load_manifest,
    load_runtime_values,
    parse_postgres_url,
    safe_child_path,
)


STATUS_CODE = {"OK": 0, "WARNING": 1, "CRITICAL": 2}
MONITOR_DATABASE_URL_KEY = "MES_MONITOR_DATABASE_URL"


def _is_link(path: Path) -> bool:
    return path.is_symlink() or (
        hasattr(path, "is_junction") and path.is_junction()
    )


@dataclass(frozen=True)
class Thresholds:
    connection_warning_ratio: float = 0.60
    connection_critical_ratio: float = 0.80
    disk_warning_free_ratio: float = 0.20
    disk_critical_free_ratio: float = 0.10
    lock_warning_seconds: int = 5
    lock_critical_seconds: int = 30
    query_warning_seconds: int = 30
    query_critical_seconds: int = 150
    idle_transaction_warning_seconds: int = 30
    idle_transaction_critical_seconds: int = 60
    backup_warning_hours: int = 26
    backup_critical_hours: int = 48
    restore_warning_days: int = 90
    restore_critical_days: int = 120
    dead_tuple_warning_count: int = 10_000
    dead_tuple_warning_ratio: float = 0.20
    dead_tuple_critical_count: int = 100_000
    dead_tuple_critical_ratio: float = 0.40


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    summary: str
    metrics: dict[str, object]


def _status_for_higher_ratio(
    value: float,
    warning: float,
    critical: float,
) -> str:
    if value >= critical:
        return "CRITICAL"
    if value >= warning:
        return "WARNING"
    return "OK"


def _status_for_higher_value(
    value: float,
    warning: float,
    critical: float,
) -> str:
    return _status_for_higher_ratio(value, warning, critical)


def _status_for_lower_ratio(
    value: float,
    warning: float,
    critical: float,
) -> str:
    if value <= critical:
        return "CRITICAL"
    if value <= warning:
        return "WARNING"
    return "OK"


def _load_monitor_database_url(
    app_env_file: Path,
    monitor_env_file: Path | None,
) -> tuple[str, str]:
    process_value = os.environ.get(MONITOR_DATABASE_URL_KEY, "").strip()
    if process_value:
        return process_value, "process_environment"

    if monitor_env_file is not None:
        values = dotenv_values(monitor_env_file)
        monitor_value = str(
            values.get(MONITOR_DATABASE_URL_KEY)
            or values.get("DATABASE_URL")
            or ""
        ).strip()
        if not monitor_value:
            raise ValueError(
                "Monitor env file must contain MES_MONITOR_DATABASE_URL or DATABASE_URL"
            )
        return monitor_value, "monitor_env_file"

    app_values = load_runtime_values(app_env_file)
    app_value = app_values.get("DATABASE_URL", "").strip()
    if not app_value:
        raise ValueError("DATABASE_URL is missing")
    return app_value, "application_fallback"


def _query_database(database_url: str) -> dict[str, object]:
    connection_info = parse_postgres_url(database_url)
    connect_kwargs = connection_info.connect_kwargs()
    connect_kwargs.update(
        connect_timeout=5,
        application_name="mes-operations-check",
        row_factory=dict_row,
    )

    result: dict[str, object] = {}
    with psycopg.connect(**connect_kwargs) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            cursor.execute("SET LOCAL statement_timeout = '10s'")

            cursor.execute(
                """
                SELECT current_database() AS database_name,
                       current_user AS database_user,
                       current_setting('server_version') AS server_version,
                       pg_database_size(current_database()) AS database_bytes,
                       current_setting('max_connections')::integer AS max_connections,
                       current_setting('autovacuum') AS autovacuum,
                       current_setting('track_counts') AS track_counts,
                       pg_has_role(current_user, 'pg_monitor', 'MEMBER') AS has_pg_monitor,
                       EXISTS (
                           SELECT 1 FROM pg_extension
                           WHERE extname = 'pg_stat_statements'
                       ) AS pg_stat_statements_installed
                """
            )
            result["server"] = dict(cursor.fetchone())

            cursor.execute(
                """
                SELECT count(*) FILTER (WHERE pid <> pg_backend_pid()) AS used_connections,
                       count(*) FILTER (
                           WHERE pid <> pg_backend_pid()
                             AND wait_event_type = 'Lock'
                       ) AS lock_waiters,
                       COALESCE(max(EXTRACT(EPOCH FROM (
                           clock_timestamp() - query_start
                       ))) FILTER (
                           WHERE pid <> pg_backend_pid()
                             AND wait_event_type = 'Lock'
                       ), 0)::bigint AS longest_lock_wait_seconds,
                       COALESCE(max(EXTRACT(EPOCH FROM (
                           clock_timestamp() - query_start
                       ))) FILTER (
                           WHERE pid <> pg_backend_pid()
                             AND state = 'active'
                       ), 0)::bigint AS longest_active_query_seconds,
                       COALESCE(max(EXTRACT(EPOCH FROM (
                           clock_timestamp() - xact_start
                       ))) FILTER (
                           WHERE pid <> pg_backend_pid()
                             AND state = 'idle in transaction'
                       ), 0)::bigint AS longest_idle_transaction_seconds
                FROM pg_stat_activity
                """
            )
            result["activity"] = dict(cursor.fetchone())

            cursor.execute(
                """
                SELECT deadlocks, temp_files, temp_bytes, stats_reset
                FROM pg_stat_database
                WHERE datname = current_database()
                """
            )
            result["database_stats"] = dict(cursor.fetchone())

            cursor.execute(
                """
                SELECT count(*) FILTER (
                           WHERE NOT i.indisvalid OR NOT i.indisready
                       ) AS invalid_indexes,
                       count(*) AS total_indexes,
                       COALESCE(sum(pg_relation_size(s.indexrelid)), 0) AS index_bytes
                FROM pg_stat_user_indexes s
                JOIN pg_index i ON i.indexrelid = s.indexrelid
                """
            )
            result["indexes"] = dict(cursor.fetchone())

            cursor.execute(
                """
                SELECT relname AS table_name,
                       n_live_tup,
                       n_dead_tup,
                       n_mod_since_analyze,
                       last_analyze,
                       last_autoanalyze,
                       last_autovacuum
                FROM pg_stat_user_tables
                WHERE n_dead_tup >= %s
                ORDER BY n_dead_tup DESC
                LIMIT 20
                """,
                (Thresholds().dead_tuple_warning_count,),
            )
            result["dead_tuple_tables"] = [dict(row) for row in cursor.fetchall()]

            cursor.execute(
                """
                SELECT count(*) AS never_analyzed_tables
                FROM pg_stat_user_tables s
                JOIN pg_class c ON c.oid = s.relid
                WHERE c.reltuples < 0
                  AND (s.n_live_tup > 0 OR s.n_mod_since_analyze > 0)
                """
            )
            result["planner_stats"] = dict(cursor.fetchone())

            if bool(result["server"]["has_pg_monitor"]):
                cursor.execute(
                    "SELECT current_setting('shared_preload_libraries') AS value"
                )
                result["shared_preload_libraries"] = cursor.fetchone()["value"]
            else:
                result["shared_preload_libraries"] = None

    return result


def _database_checks(
    snapshot: Mapping[str, object],
    connection_source: str,
    thresholds: Thresholds,
) -> list[CheckResult]:
    server = snapshot["server"]
    activity = snapshot["activity"]
    database_stats = snapshot["database_stats"]
    indexes = snapshot["indexes"]
    planner_stats = snapshot["planner_stats"]
    results: list[CheckResult] = []

    results.append(
        CheckResult(
            name="database_connectivity",
            status="OK",
            summary="PostgreSQL connection and read-only queries succeeded",
            metrics={
                "database": server["database_name"],
                "server_version": server["server_version"],
                "database_bytes": int(server["database_bytes"]),
                "connection_source": connection_source,
            },
        )
    )

    used_connections = int(activity["used_connections"])
    max_connections = int(server["max_connections"])
    connection_ratio = used_connections / max_connections if max_connections else 1.0
    results.append(
        CheckResult(
            name="connection_usage",
            status=_status_for_higher_ratio(
                connection_ratio,
                thresholds.connection_warning_ratio,
                thresholds.connection_critical_ratio,
            ),
            summary=f"{used_connections} of {max_connections} PostgreSQL connections are in use",
            metrics={
                "used": used_connections,
                "maximum": max_connections,
                "ratio": round(connection_ratio, 4),
            },
        )
    )

    lock_seconds = int(activity["longest_lock_wait_seconds"])
    results.append(
        CheckResult(
            name="lock_waits",
            status=_status_for_higher_value(
                lock_seconds,
                thresholds.lock_warning_seconds,
                thresholds.lock_critical_seconds,
            ),
            summary=f"Longest current lock wait is {lock_seconds} seconds",
            metrics={
                "waiters": int(activity["lock_waiters"]),
                "longest_seconds": lock_seconds,
            },
        )
    )

    query_seconds = int(activity["longest_active_query_seconds"])
    results.append(
        CheckResult(
            name="long_running_queries",
            status=_status_for_higher_value(
                query_seconds,
                thresholds.query_warning_seconds,
                thresholds.query_critical_seconds,
            ),
            summary=f"Longest active query is {query_seconds} seconds",
            metrics={"longest_seconds": query_seconds},
        )
    )

    idle_seconds = int(activity["longest_idle_transaction_seconds"])
    results.append(
        CheckResult(
            name="idle_transactions",
            status=_status_for_higher_value(
                idle_seconds,
                thresholds.idle_transaction_warning_seconds,
                thresholds.idle_transaction_critical_seconds,
            ),
            summary=f"Longest idle transaction is {idle_seconds} seconds",
            metrics={"longest_seconds": idle_seconds},
        )
    )

    autovacuum_ok = server["autovacuum"] == "on" and server["track_counts"] == "on"
    results.append(
        CheckResult(
            name="automatic_maintenance",
            status="OK" if autovacuum_ok else "CRITICAL",
            summary=(
                "Autovacuum and statistics collection are enabled"
                if autovacuum_ok
                else "Autovacuum or statistics collection is disabled"
            ),
            metrics={
                "autovacuum": server["autovacuum"],
                "track_counts": server["track_counts"],
            },
        )
    )

    dead_table_status = "OK"
    dead_table_names: list[str] = []
    critical_dead_table_names: list[str] = []
    for table in snapshot["dead_tuple_tables"]:
        live = int(table["n_live_tup"])
        dead = int(table["n_dead_tup"])
        ratio = dead / max(live + dead, 1)
        if (
            dead >= thresholds.dead_tuple_critical_count
            and ratio >= thresholds.dead_tuple_critical_ratio
        ):
            critical_dead_table_names.append(str(table["table_name"]))
        elif ratio >= thresholds.dead_tuple_warning_ratio:
            dead_table_names.append(str(table["table_name"]))
    if critical_dead_table_names:
        dead_table_status = "CRITICAL"
    elif dead_table_names:
        dead_table_status = "WARNING"
    results.append(
        CheckResult(
            name="dead_tuples",
            status=dead_table_status,
            summary=(
                "No table exceeds the dead-tuple alert thresholds"
                if dead_table_status == "OK"
                else "One or more tables exceed the dead-tuple alert thresholds"
            ),
            metrics={
                "warning_tables": dead_table_names,
                "critical_tables": critical_dead_table_names,
            },
        )
    )

    invalid_indexes = int(indexes["invalid_indexes"])
    results.append(
        CheckResult(
            name="index_integrity",
            status="CRITICAL" if invalid_indexes else "OK",
            summary=(
                f"{invalid_indexes} invalid or incomplete indexes found"
                if invalid_indexes
                else "All indexes are valid and ready"
            ),
            metrics={
                "invalid_indexes": invalid_indexes,
                "total_indexes": int(indexes["total_indexes"]),
                "index_bytes": int(indexes["index_bytes"]),
            },
        )
    )

    never_analyzed = int(planner_stats["never_analyzed_tables"])
    results.append(
        CheckResult(
            name="planner_statistics",
            status="WARNING" if never_analyzed else "OK",
            summary=(
                f"{never_analyzed} populated tables have never been analyzed"
                if never_analyzed
                else "Planner statistics exist for populated tables"
            ),
            metrics={"never_analyzed_tables": never_analyzed},
        )
    )

    has_monitor = bool(server["has_pg_monitor"])
    results.append(
        CheckResult(
            name="monitoring_privileges",
            status="OK" if has_monitor else "WARNING",
            summary=(
                "The connection has the PostgreSQL pg_monitor role"
                if has_monitor
                else "The connection lacks pg_monitor; server-wide detail is limited"
            ),
            metrics={"has_pg_monitor": has_monitor},
        )
    )

    extension_installed = bool(server["pg_stat_statements_installed"])
    preload_value = snapshot.get("shared_preload_libraries")
    preloaded = bool(
        preload_value
        and "pg_stat_statements" in {
            item.strip() for item in str(preload_value).split(",")
        }
    )
    pg_stat_ok = extension_installed and preloaded
    results.append(
        CheckResult(
            name="query_statistics",
            status="OK" if pg_stat_ok else "WARNING",
            summary=(
                "pg_stat_statements is available for normalized query monitoring"
                if pg_stat_ok
                else "pg_stat_statements is not fully enabled"
            ),
            metrics={
                "extension_installed": extension_installed,
                "preload_verified": preloaded if has_monitor else None,
            },
        )
    )

    results.append(
        CheckResult(
            name="database_incidents",
            status="WARNING" if int(database_stats["deadlocks"]) else "OK",
            summary=(
                f"{int(database_stats['deadlocks'])} cumulative deadlocks are recorded"
                if int(database_stats["deadlocks"])
                else "No cumulative deadlocks are recorded"
            ),
            metrics={
                "deadlocks": int(database_stats["deadlocks"]),
                "temp_files": int(database_stats["temp_files"]),
                "temp_bytes": int(database_stats["temp_bytes"]),
                "stats_reset": (
                    database_stats["stats_reset"].isoformat()
                    if database_stats["stats_reset"]
                    else None
                ),
            },
        )
    )
    return results


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a UTC offset")
    return parsed.astimezone(UTC)


def _backup_check(
    backup_root: Path | None,
    now: datetime,
    thresholds: Thresholds,
) -> CheckResult:
    if backup_root is None:
        return CheckResult(
            "backup_age",
            "WARNING",
            "Backup root was not supplied",
            {},
        )
    try:
        root = backup_root.resolve(strict=True)
    except OSError:
        return CheckResult(
            "backup_age",
            "CRITICAL",
            "Backup root does not exist or is not accessible",
            {"backup_root": str(backup_root)},
        )
    candidates: list[tuple[datetime, Path, dict[str, object]]] = []
    for child in root.iterdir():
        if (
            not child.is_dir()
            or child.name.startswith(".")
            or _is_link(child)
        ):
            continue
        manifest_path = child / "manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            manifest = load_manifest(child)
            created_at = _parse_utc(str(manifest["created_at_utc"]))
            database = manifest["database"]
            dump_path = safe_child_path(child, str(database["dump_file"]))
            if dump_path.stat().st_size != int(database["dump_bytes"]):
                continue
            for storage_set in manifest["storage_sets"]:
                storage_path = safe_child_path(
                    child,
                    str(storage_set["backup_path"]),
                )
                if not storage_path.is_dir():
                    raise ValueError("Backup storage path is missing")
        except (KeyError, OSError, RuntimeError, TypeError, ValueError):
            continue
        candidates.append((created_at, child, manifest))

    if not candidates:
        return CheckResult(
            "backup_age",
            "CRITICAL",
            "No valid completed MES backup was found",
            {"backup_root": str(root)},
        )

    created_at, directory, manifest = max(candidates, key=lambda item: item[0])
    age_hours = max(0.0, (now - created_at).total_seconds() / 3600)
    status = _status_for_higher_value(
        age_hours,
        thresholds.backup_warning_hours,
        thresholds.backup_critical_hours,
    )
    return CheckResult(
        "backup_age",
        status,
        f"Latest completed backup is {age_hours:.1f} hours old",
        {
            "backup_id": manifest["backup_id"],
            "backup_directory": str(directory),
            "created_at_utc": created_at.isoformat(),
            "age_hours": round(age_hours, 2),
        },
    )


def _restore_rehearsal_check(
    record_path: Path | None,
    now: datetime,
    thresholds: Thresholds,
) -> CheckResult:
    if record_path is None:
        return CheckResult(
            "restore_rehearsal_age",
            "WARNING",
            "Restore rehearsal record path was not supplied",
            {},
        )
    try:
        payload = json.loads(record_path.read_text(encoding="utf-8"))
        verified_at = _parse_utc(str(payload["verified_at_utc"]))
        backup_id = str(payload["backup_id"])
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return CheckResult(
            "restore_rehearsal_age",
            "CRITICAL",
            "No valid restore rehearsal record was found",
            {"record_path": str(record_path)},
        )

    age_days = max(0.0, (now - verified_at).total_seconds() / 86400)
    status = _status_for_higher_value(
        age_days,
        thresholds.restore_warning_days,
        thresholds.restore_critical_days,
    )
    return CheckResult(
        "restore_rehearsal_age",
        status,
        f"Last verified restore rehearsal is {age_days:.1f} days old",
        {
            "backup_id": backup_id,
            "verified_at_utc": verified_at.isoformat(),
            "age_days": round(age_days, 2),
        },
    )


def _disk_check(paths: Iterable[Path], thresholds: Thresholds) -> CheckResult:
    volumes: dict[str, dict[str, object]] = {}
    errors: list[str] = []
    worst_status = "OK"
    for path in paths:
        try:
            resolved = path.resolve(strict=True)
            usage = shutil.disk_usage(resolved)
        except OSError:
            errors.append(str(path))
            continue
        free_ratio = usage.free / usage.total if usage.total else 0.0
        status = _status_for_lower_ratio(
            free_ratio,
            thresholds.disk_warning_free_ratio,
            thresholds.disk_critical_free_ratio,
        )
        if STATUS_CODE[status] > STATUS_CODE[worst_status]:
            worst_status = status
        volume_key = resolved.anchor or str(resolved)
        volumes[volume_key] = {
            "total_bytes": usage.total,
            "free_bytes": usage.free,
            "free_ratio": round(free_ratio, 4),
        }

    if errors:
        worst_status = "CRITICAL"
    return CheckResult(
        "disk_capacity",
        worst_status,
        (
            "All monitored volumes have sufficient free space"
            if worst_status == "OK"
            else "One or more monitored paths or volumes require attention"
        ),
        {"volumes": volumes, "unavailable_paths": errors},
    )


def _build_report(
    checks: list[CheckResult],
    generated_at: datetime,
) -> dict[str, object]:
    exit_code = max(STATUS_CODE[item.status] for item in checks)
    overall_status = next(
        status for status, code in STATUS_CODE.items() if code == exit_code
    )
    return {
        "format_version": 1,
        "generated_at_utc": generated_at.isoformat(),
        "overall_status": overall_status,
        "exit_code": exit_code,
        "checks": [asdict(item) for item in checks],
    }


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _write_history(history_root: Path, report: Mapping[str, object]) -> Path:
    history_root = history_root.resolve()
    history_root.mkdir(parents=True, exist_ok=True)
    generated_at = _parse_utc(str(report["generated_at_utc"]))
    output = history_root / generated_at.strftime("mes-operations-%Y%m%dT%H%M%SZ.json")
    if output.exists():
        raise FileExistsError(f"Operations history already exists: {output}")
    _write_json_atomic(output, report)
    return output


def _render_text(report: Mapping[str, object]) -> str:
    lines = [
        f"MES operations status: {report['overall_status']}",
        f"Generated UTC: {report['generated_at_utc']}",
    ]
    for check in report["checks"]:
        lines.append(
            f"[{check['status']}] {check['name']}: {check['summary']}"
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run read-only PostgreSQL and MES operations checks."
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=BACKEND_ROOT / ".env",
    )
    parser.add_argument("--monitor-env-file", type=Path)
    parser.add_argument("--backup-root", type=Path)
    parser.add_argument(
        "--storage-root",
        type=Path,
        action="append",
        help=(
            "Effective MES file storage root. Repeat for distinct roots. "
            "Overrides storage paths from the application env file."
        ),
    )
    parser.add_argument("--restore-record", type=Path)
    parser.add_argument("--history-root", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    now = datetime.now(UTC)
    thresholds = Thresholds()
    database_url, connection_source = _load_monitor_database_url(
        args.env_file,
        args.monitor_env_file,
    )
    snapshot = _query_database(database_url)
    checks = _database_checks(snapshot, connection_source, thresholds)

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
        app_values = load_runtime_values(args.env_file)
        storage_roots = collect_storage_roots(app_values)
    monitored_paths = [item["source"] for item in storage_roots]
    if args.backup_root is not None:
        monitored_paths.append(args.backup_root)

    checks.append(_backup_check(args.backup_root, now, thresholds))
    checks.append(
        _restore_rehearsal_check(args.restore_record, now, thresholds)
    )
    checks.append(_disk_check(monitored_paths, thresholds))
    report = _build_report(checks, now)

    if args.history_root is not None:
        history_path = _write_history(args.history_root, report)
        report["history_file"] = str(history_path)
    if args.output_json is not None:
        _write_json_atomic(args.output_json.resolve(), report)

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=True, indent=2, default=str))
    else:
        print(_render_text(report))
    return int(report["exit_code"])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(
            f"operations_check_failed={type(exc).__name__}",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
