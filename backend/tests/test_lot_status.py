from __future__ import annotations

import unittest

from app.services.lot_status import derive_lot_status_from_inspection_statuses


class LotStatusPolicyTests(unittest.TestCase):
    def test_active_inspection_status_takes_priority_over_completed_history(self) -> None:
        self.assertEqual(
            "RECEIVED",
            derive_lot_status_from_inspection_statuses(
                ["PARTIAL_DONE", "RECEIVED"]
            ),
        )
        self.assertEqual(
            "WAITING",
            derive_lot_status_from_inspection_statuses(
                ["PARTIAL_DONE", "WAITING"]
            ),
        )

    def test_final_done_completes_lot_after_partial_inspection_history(self) -> None:
        self.assertEqual(
            "DONE",
            derive_lot_status_from_inspection_statuses(
                ["PARTIAL_DONE", "DONE"]
            ),
        )

    def test_partial_only_and_canceled_only_states_are_handled(self) -> None:
        self.assertEqual(
            "PARTIAL_DONE",
            derive_lot_status_from_inspection_statuses(["PARTIAL_DONE"]),
        )
        self.assertIsNone(
            derive_lot_status_from_inspection_statuses(["CANCELED"])
        )


if __name__ == "__main__":
    unittest.main()
