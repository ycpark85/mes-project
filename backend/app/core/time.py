from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


UTC = timezone.utc
KOREA_TIME_ZONE = ZoneInfo("Asia/Seoul")


def utc_now() -> datetime:
    return datetime.now(UTC)


def korea_now() -> datetime:
    return datetime.now(KOREA_TIME_ZONE)


def korea_today() -> date:
    return korea_now().date()


def to_korea_time(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware datetime is required")
    return value.astimezone(KOREA_TIME_ZONE)


def korea_day_bounds_utc(value: date) -> tuple[datetime, datetime]:
    start_korea = datetime.combine(value, time.min, tzinfo=KOREA_TIME_ZONE)
    end_korea = start_korea + timedelta(days=1)
    return start_korea.astimezone(UTC), end_korea.astimezone(UTC)
