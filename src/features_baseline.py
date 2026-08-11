from __future__ import annotations

import numpy as np
import pandas as pd


ID_COLUMNS = ["user_id", "order_id", "eval_set", "order_number"]


def _expanding_mean_to_date(df: pd.DataFrame, col: str) -> pd.Series:
    valid = df[col].notna()
    cumulative = df[col].fillna(0).groupby(df["user_id"], sort=False).cumsum()
    valid_count = valid.astype("int32").groupby(df["user_id"], sort=False).cumsum()
    return (cumulative / valid_count.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)


def build_baseline_features(order_behavior: pd.DataFrame) -> pd.DataFrame:
    """Build traditional baseline features for fair comparison with leading signals.

    The unit is a user-order snapshot after the current order. These features intentionally
    describe broad customer history and current snapshot metadata rather than recent decay.
    """
    required = {
        "user_id",
        "order_id",
        "eval_set",
        "order_number",
        "order_dow",
        "order_hour_of_day",
        "days_since_prior_order",
        "relative_day",
        "item_count",
        "reorder_ratio",
    }
    missing = required - set(order_behavior.columns)
    if missing:
        raise ValueError(f"Missing required baseline feature inputs: {sorted(missing)}")

    out = order_behavior.sort_values(["user_id", "order_number", "order_id"]).copy()
    out["base_user_tenure_days"] = out["relative_day"]
    out["base_total_orders_to_date"] = out["order_number"]
    out["base_avg_days_between_orders"] = _expanding_mean_to_date(out, "days_since_prior_order")
    out["base_avg_basket_size_to_date"] = _expanding_mean_to_date(out, "item_count")
    out["base_avg_reorder_ratio_to_date"] = _expanding_mean_to_date(out, "reorder_ratio")
    out["base_order_dow"] = out["order_dow"]
    out["base_order_hour"] = out["order_hour_of_day"]

    feature_cols = [
        "base_user_tenure_days",
        "base_total_orders_to_date",
        "base_avg_days_between_orders",
        "base_avg_basket_size_to_date",
        "base_avg_reorder_ratio_to_date",
        "base_order_dow",
        "base_order_hour",
    ]
    return out[ID_COLUMNS + feature_cols]
