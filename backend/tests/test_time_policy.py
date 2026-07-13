from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from app.core.time import (
    KOREA_TIME_ZONE,
    korea_day_bounds_utc,
    to_korea_time,
    utc_now,
)


class TimePolicyTests(unittest.TestCase):
    def test_utc_now_returns_timezone_aware_utc_datetime(self) -> None:
        value = utc_now()

        self.assertIsNotNone(value.tzinfo)
        self.assertEqual(timezone.utc, value.tzinfo)
        self.assertEqual(0, value.utcoffset().total_seconds())

    def test_korea_day_bounds_are_converted_to_half_open_utc_range(self) -> None:
        start, end_exclusive = korea_day_bounds_utc(date(2026, 7, 13))

        self.assertEqual(
            datetime(2026, 7, 12, 15, 0, tzinfo=timezone.utc),
            start,
        )
        self.assertEqual(
            datetime(2026, 7, 13, 15, 0, tzinfo=timezone.utc),
            end_exclusive,
        )

    def test_to_korea_time_converts_utc_and_rejects_naive_datetime(self) -> None:
        converted = to_korea_time(
            datetime(2026, 7, 13, 2, 0, tzinfo=timezone.utc)
        )

        self.assertEqual(datetime(2026, 7, 13, 11, 0), converted.replace(tzinfo=None))
        self.assertEqual(KOREA_TIME_ZONE, converted.tzinfo)

        with self.assertRaises(ValueError):
            to_korea_time(datetime(2026, 7, 13, 11, 0))


if __name__ == "__main__":
    unittest.main()
