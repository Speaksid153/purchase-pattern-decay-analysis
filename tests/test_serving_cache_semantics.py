from __future__ import annotations

import unittest

import pandas as pd

from scripts.serving_cache_common import orders_through_snapshot, snapshot_gap_metrics


class ServingCacheSemanticTests(unittest.TestCase):
    def test_orders_are_limited_to_scored_snapshot(self) -> None:
        orders = pd.DataFrame(
            [
                {"order_id": 10, "order_number": 1, "days_since_prior_order": None},
                {"order_id": 20, "order_number": 2, "days_since_prior_order": 30.0},
                {"order_id": 30, "order_number": 3, "days_since_prior_order": 0.0},
            ]
        )

        snapshot = orders_through_snapshot(orders, 20)

        self.assertEqual(snapshot["order_id"].tolist(), [10, 20])
        self.assertEqual(snapshot["days_since_prior_order"].dropna().tolist(), [30.0])

    def test_historical_gap_excludes_the_scored_gap(self) -> None:
        snapshot = pd.DataFrame(
            [
                {"order_id": 10, "order_number": 1, "days_since_prior_order": None},
                {"order_id": 20, "order_number": 2, "days_since_prior_order": 5.0},
                {"order_id": 30, "order_number": 3, "days_since_prior_order": 20.0},
            ]
        )

        latest_gap, historical_average = snapshot_gap_metrics(snapshot)

        self.assertEqual(latest_gap, 20.0)
        self.assertEqual(historical_average, 5.0)

    def test_missing_scored_order_fails_closed(self) -> None:
        orders = pd.DataFrame(
            [{"order_id": 10, "order_number": 1, "days_since_prior_order": None}]
        )

        with self.assertRaisesRegex(ValueError, "Expected one scored order"):
            orders_through_snapshot(orders, 999)


if __name__ == "__main__":
    unittest.main()
