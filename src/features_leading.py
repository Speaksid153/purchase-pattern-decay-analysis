from __future__ import annotations

import numpy as np
import pandas as pd


ID_COLUMNS = ["user_id", "order_id", "eval_set", "order_number"]


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    ratio = numerator / denominator.replace(0, np.nan)
    return ratio.replace([np.inf, -np.inf], np.nan)


def _recent_mean_vs_prior(
    df: pd.DataFrame,
    col: str,
    prior_col: str,
    *,
    window: int = 3,
    min_recent_periods: int = 2,
) -> pd.DataFrame:
    recent_values = [
        df.groupby("user_id", sort=False)[col].shift(i)
        for i in range(0, window)
    ]
    recent_frame = pd.concat(recent_values, axis=1)
    recent = recent_frame.mean(axis=1, skipna=True).where(recent_frame.notna().sum(axis=1) >= min_recent_periods)
    prior = df[prior_col]
    return pd.DataFrame(
        {
            f"{col}_recent{window}_avg": recent,
            f"{col}_prior_to_current_avg": prior,
            f"{col}_recent{window}_ratio_to_prior": _safe_ratio(recent, prior),
            f"{col}_recent{window}_delta_from_prior": recent - prior,
        },
        index=df.index,
    )


def _last3_slope(series: pd.Series) -> pd.Series:
    return (series - series.shift(2)) / 2


def add_purchase_cadence_decay(customer_orders: pd.DataFrame) -> pd.DataFrame:
    """Add cadence features from current and historical gaps only.

    Positive gap slopes mean the customer is waiting longer between orders.
    Negative frequency slopes mean purchase frequency is declining.
    """
    out = customer_orders.copy()
    grouped_gap = out.groupby("user_id", sort=False)["days_since_prior_order"]
    if "historical_median_gap_days" in out.columns:
        out["historical_median_gap_days_feature"] = out["historical_median_gap_days"]
    else:
        out["historical_median_gap_days_feature"] = out["prior_avg_gap_days"]
    out["current_gap_ratio_to_historical_median"] = _safe_ratio(
        out["days_since_prior_order"], out["historical_median_gap_days_feature"]
    )
    out["current_gap_gt_1_5x_historical_median"] = out["current_gap_ratio_to_historical_median"].ge(1.5)
    out["current_gap_gt_2x_historical_median"] = out["current_gap_ratio_to_historical_median"].ge(2.0)
    out["gap_slope_last3"] = (out["days_since_prior_order"] - grouped_gap.shift(2)) / 2

    positive_gap = out["days_since_prior_order"].where(out["days_since_prior_order"].gt(0))
    out["_purchase_frequency"] = 1 / positive_gap
    out["purchase_frequency_slope_last3"] = (
        out["_purchase_frequency"] - out.groupby("user_id", sort=False)["_purchase_frequency"].shift(2)
    ) / 2
    return out.drop(columns=["_purchase_frequency"])


def add_gap_acceleration(customer_orders: pd.DataFrame) -> pd.DataFrame:
    """Add latest-gap acceleration features versus the user's earlier rhythm."""
    out = customer_orders.copy()
    grouped_gap = out.groupby("user_id", sort=False)["days_since_prior_order"]
    if "prior_avg_gap_days" in out.columns:
        prior_avg_gap = out["prior_avg_gap_days"]
    else:
        gap_sum = out["days_since_prior_order"].fillna(0).groupby(out["user_id"], sort=False).cumsum()
        gap_count = out["days_since_prior_order"].notna().astype("int32").groupby(out["user_id"], sort=False).cumsum()
        prior_avg_gap = (gap_sum - out["days_since_prior_order"].fillna(0)) / (
            gap_count - out["days_since_prior_order"].notna().astype("int32")
        ).replace(0, np.nan)
    previous_gap = grouped_gap.shift(1)
    out["prior_avg_gap_days_feature"] = prior_avg_gap
    out["previous_gap_days"] = previous_gap
    out["latest_gap_ratio_to_prior_avg"] = _safe_ratio(out["days_since_prior_order"], prior_avg_gap)
    out["latest_gap_ratio_to_previous_gap"] = _safe_ratio(out["days_since_prior_order"], previous_gap)
    out["gap_acceleration_1_5x_flag"] = out["latest_gap_ratio_to_prior_avg"].ge(1.5)
    return out


def add_basket_size_trend(customer_orders: pd.DataFrame) -> pd.DataFrame:
    """Add recent basket-size trend features using item counts.

    Instacart order-product rows are unique per product within an order, so
    unique_product_count duplicates item_count and is intentionally not emitted.
    """
    out = customer_orders.copy()
    out = out.join(_recent_mean_vs_prior(out, "item_count", "prior_avg_item_count"))
    out["basket_size_decay_flag"] = out["item_count_recent3_ratio_to_prior"].lt(0.85)
    return out


def add_reorder_behavior_decay(customer_orders: pd.DataFrame) -> pd.DataFrame:
    """Add reorder-routine decay features."""
    out = customer_orders.copy()
    trend = _recent_mean_vs_prior(out, "reorder_ratio", "prior_avg_reorder_ratio", min_recent_periods=2)
    out = out.join(trend)
    out["reorder_ratio_slope_last3"] = (
        out["reorder_ratio"] - out.groupby("user_id", sort=False)["reorder_ratio"].shift(2)
    ) / 2
    out["reorder_behavior_decay_flag"] = (
        out["reorder_ratio_recent3_delta_from_prior"].lt(-0.10)
        | out["reorder_ratio_slope_last3"].lt(-0.05)
    )
    return out


def add_category_diversity_narrowing(customer_orders: pd.DataFrame) -> pd.DataFrame:
    """Add recent aisle/department narrowing features."""
    out = customer_orders.copy()
    out = out.join(
        _recent_mean_vs_prior(
            out,
            "distinct_department_count",
            "prior_avg_distinct_department_count",
        )
    )
    out = out.join(
        _recent_mean_vs_prior(
            out,
            "distinct_aisle_count",
            "prior_avg_distinct_aisle_count",
        )
    )
    out["category_diversity_narrowing_flag"] = (
        out["distinct_department_count_recent3_ratio_to_prior"].lt(0.85)
        | out["distinct_aisle_count_recent3_ratio_to_prior"].lt(0.85)
    )
    return out


def _circular_distance(values: pd.Series, reference: pd.Series, period: int) -> pd.Series:
    raw = (values - reference).abs()
    return pd.concat([raw, period - raw], axis=1).min(axis=1)


def add_time_consistency_decay(customer_orders: pd.DataFrame) -> pd.DataFrame:
    """Add drift from the user's prior order day/hour pattern."""
    out = customer_orders.copy()

    for col, period in [("order_hour_of_day", 24), ("order_dow", 7)]:
        radians = 2 * np.pi * out[col] / period
        sin_col = f"_{col}_sin"
        cos_col = f"_{col}_cos"
        out[sin_col] = np.sin(radians)
        out[cos_col] = np.cos(radians)
        sin_sum = out[sin_col].groupby(out["user_id"], sort=False).cumsum()
        cos_sum = out[cos_col].groupby(out["user_id"], sort=False).cumsum()
        order_count = out.groupby("user_id", sort=False).cumcount() + 1
        prior_count = order_count - 1
        prior_sin = (sin_sum - out[sin_col]) / prior_count.replace(0, np.nan)
        prior_cos = (cos_sum - out[cos_col]) / prior_count.replace(0, np.nan)
        prior_sin = prior_sin.where(prior_count >= 2)
        prior_cos = prior_cos.where(prior_count >= 2)
        prior_angle = np.arctan2(prior_sin, prior_cos)
        prior_pattern = (prior_angle * period / (2 * np.pi)) % period
        distance_col = "hour_distance_from_prior_pattern" if col == "order_hour_of_day" else "dow_distance_from_prior_pattern"
        out[distance_col] = _circular_distance(out[col], prior_pattern, period)
        out = out.drop(columns=[sin_col, cos_col])

    out["time_consistency_decay_flag"] = (
        out["hour_distance_from_prior_pattern"].ge(6)
        | out["dow_distance_from_prior_pattern"].ge(2)
    )
    return out


def add_reliability_features(customer_orders: pd.DataFrame) -> pd.DataFrame:
    """Add history-depth features used for ranking warning confidence."""
    out = customer_orders.copy()
    grouped = out.groupby("user_id", sort=False)
    out["behavior_orders_to_date"] = grouped.cumcount() + 1
    out["known_gap_count_feature"] = (
        out["days_since_prior_order"].notna().astype("int32").groupby(out["user_id"]).cumsum()
    )
    out["trend_history_available"] = out["behavior_orders_to_date"].ge(5)
    out["history_reliability_score"] = np.select(
        [
            out["known_gap_count_feature"].ge(9),
            out["known_gap_count_feature"].ge(5),
            out["known_gap_count_feature"].ge(3),
        ],
        [1.0, 0.85, 0.70],
        default=0.35,
    )
    return out


def build_leading_features(order_behavior: pd.DataFrame) -> pd.DataFrame:
    """Build leakage-safe leading behavioral decay features.

    Input rows must be user-order snapshots. The function does not use any next-order
    columns, labels, or target severity columns.
    """
    required = {
        "user_id",
        "order_id",
        "eval_set",
        "order_number",
        "order_dow",
        "order_hour_of_day",
        "days_since_prior_order",
        "item_count",
        "distinct_aisle_count",
        "distinct_department_count",
        "reorder_ratio",
        "prior_avg_gap_days",
        "prior_avg_item_count",
        "prior_avg_reorder_ratio",
        "prior_avg_distinct_department_count",
        "prior_avg_distinct_aisle_count",
    }
    missing = required - set(order_behavior.columns)
    if missing:
        raise ValueError(f"Missing required feature inputs: {sorted(missing)}")

    out = order_behavior.sort_values(["user_id", "order_number", "order_id"]).copy()
    out = add_purchase_cadence_decay(out)
    out = add_gap_acceleration(out)
    out = add_basket_size_trend(out)
    out = add_reorder_behavior_decay(out)
    out = add_category_diversity_narrowing(out)
    out = add_time_consistency_decay(out)
    out = add_reliability_features(out)

    feature_cols = [
        "historical_median_gap_days_feature",
        "current_gap_ratio_to_historical_median",
        "current_gap_gt_1_5x_historical_median",
        "current_gap_gt_2x_historical_median",
        "gap_slope_last3",
        "purchase_frequency_slope_last3",
        "prior_avg_gap_days_feature",
        "previous_gap_days",
        "latest_gap_ratio_to_prior_avg",
        "latest_gap_ratio_to_previous_gap",
        "gap_acceleration_1_5x_flag",
        "item_count_recent3_avg",
        "item_count_prior_to_current_avg",
        "item_count_recent3_ratio_to_prior",
        "item_count_recent3_delta_from_prior",
        "basket_size_decay_flag",
        "reorder_ratio_recent3_avg",
        "reorder_ratio_prior_to_current_avg",
        "reorder_ratio_recent3_ratio_to_prior",
        "reorder_ratio_recent3_delta_from_prior",
        "reorder_ratio_slope_last3",
        "reorder_behavior_decay_flag",
        "distinct_department_count_recent3_avg",
        "distinct_department_count_prior_to_current_avg",
        "distinct_department_count_recent3_ratio_to_prior",
        "distinct_department_count_recent3_delta_from_prior",
        "distinct_aisle_count_recent3_avg",
        "distinct_aisle_count_prior_to_current_avg",
        "distinct_aisle_count_recent3_ratio_to_prior",
        "distinct_aisle_count_recent3_delta_from_prior",
        "category_diversity_narrowing_flag",
        "hour_distance_from_prior_pattern",
        "dow_distance_from_prior_pattern",
        "time_consistency_decay_flag",
        "behavior_orders_to_date",
        "known_gap_count_feature",
        "trend_history_available",
        "history_reliability_score",
    ]
    return out[ID_COLUMNS + feature_cols]
