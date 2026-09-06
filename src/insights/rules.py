from __future__ import annotations

import pandas as pd

HIGH_RISK_THRESHOLD = 0.70
MEDIUM_RISK_THRESHOLD = 0.45

FEATURE_CATEGORIES: dict[str, str] = {
    "current_gap_ratio_to_historical_median": "Cadence Deterioration",
    "current_gap_gt_1_5x_historical_median": "Cadence Deterioration",
    "current_gap_gt_2x_historical_median": "Cadence Deterioration",
    "latest_gap_ratio_to_prior_avg": "Cadence Acceleration",
    "latest_gap_ratio_to_previous_gap": "Cadence Acceleration",
    "gap_acceleration_1_5x_flag": "Cadence Acceleration",
    "gap_slope_last3": "Cadence Trend",
    "purchase_frequency_slope_last3": "Frequency Decline",
    "item_count_recent3_ratio_to_prior": "Basket Shrinkage",
    "item_count_recent3_delta_from_prior": "Basket Shrinkage",
    "basket_size_decay_flag": "Basket Shrinkage",
    "reorder_ratio_recent3_delta_from_prior": "Reorder Habit Weakening",
    "reorder_ratio_slope_last3": "Reorder Habit Weakening",
    "reorder_behavior_decay_flag": "Reorder Habit Weakening",
    "distinct_department_count_recent3_ratio_to_prior": "Category Narrowing",
    "distinct_aisle_count_recent3_ratio_to_prior": "Aisle Diversity Narrowing",
    "category_diversity_narrowing_flag": "Category Diversity Narrowing",
    "hour_distance_from_prior_pattern": "Order Timing Drift",
    "dow_distance_from_prior_pattern": "Order Day Drift",
    "time_consistency_decay_flag": "Schedule Consistency Drift",
    "history_reliability_score": "History Reliability Support",
    "known_gap_count_feature": "History Depth",
    "behavior_orders_to_date": "Order Sequence Depth",
    "historical_median_gap_days_feature": "Historical Cadence",
    "previous_gap_days": "Recent Cadence",
    "prior_avg_gap_days_feature": "Historical Cadence",
    "trend_history_available": "History Reliability Support",
    "item_count_prior_to_current_avg": "Basket Baseline",
    "item_count_recent3_avg": "Recent Basket Size",
    "reorder_ratio_prior_to_current_avg": "Reorder Baseline",
    "reorder_ratio_recent3_avg": "Recent Reorder Habit",
    "reorder_ratio_recent3_ratio_to_prior": "Reorder Habit Weakening",
    "distinct_department_count_prior_to_current_avg": "Category Baseline",
    "distinct_department_count_recent3_avg": "Recent Category Breadth",
    "distinct_department_count_recent3_delta_from_prior": "Category Narrowing",
    "distinct_aisle_count_prior_to_current_avg": "Aisle Baseline",
    "distinct_aisle_count_recent3_avg": "Recent Aisle Breadth",
    "distinct_aisle_count_recent3_delta_from_prior": "Aisle Diversity Narrowing",
}

FEATURE_DESCRIPTIONS: dict[str, str] = {
    "current_gap_ratio_to_historical_median": "Purchase gap is significantly above historical normal cadence",
    "current_gap_gt_1_5x_historical_median": "Purchase gap crossed 1.5x normal customer cadence",
    "current_gap_gt_2x_historical_median": "Purchase gap crossed 2x normal customer cadence",
    "latest_gap_ratio_to_prior_avg": "Purchase gap accelerated above prior average",
    "latest_gap_ratio_to_previous_gap": "Purchase gap accelerated vs the previous gap",
    "gap_acceleration_1_5x_flag": "Purchase gap acceleration crossed warning threshold",
    "gap_slope_last3": "Inter-purchase gaps are trending upward over recent orders",
    "purchase_frequency_slope_last3": "Order frequency is declining over recent orders",
    "item_count_recent3_ratio_to_prior": "Basket size is shrinking relative to prior baseline",
    "item_count_recent3_delta_from_prior": "Basket item count dropped relative to prior baseline",
    "basket_size_decay_flag": "Recent basket size decay threshold active",
    "reorder_ratio_recent3_delta_from_prior": "Repeat-item reorder habit is weakening",
    "reorder_ratio_slope_last3": "Reorder ratio is trending downward",
    "reorder_behavior_decay_flag": "Repeat-item habit decay threshold active",
    "distinct_department_count_recent3_ratio_to_prior": "Category diversity is narrowing across departments",
    "distinct_aisle_count_recent3_ratio_to_prior": "Product aisle diversity is narrowing",
    "category_diversity_narrowing_flag": "Category diversity narrowing threshold active",
    "hour_distance_from_prior_pattern": "Order hour shifted from historical pattern",
    "dow_distance_from_prior_pattern": "Order day of week shifted from historical pattern",
    "time_consistency_decay_flag": "Order timing schedule consistency is weakening",
    "history_reliability_score": "Established order history depth provides prediction support",
    "known_gap_count_feature": "Observed purchase gap history depth",
    "behavior_orders_to_date": "Total order sequence depth to date",
    "historical_median_gap_days_feature": "Historical median purchase gap",
    "previous_gap_days": "Previous inter-purchase gap",
    "prior_avg_gap_days_feature": "Average purchase gap before the scored order",
    "trend_history_available": "Sufficient recent history is available for trend features",
    "item_count_prior_to_current_avg": "Historical average basket size",
    "item_count_recent3_avg": "Average basket size across the latest three observed orders",
    "reorder_ratio_prior_to_current_avg": "Historical repeat-item ratio",
    "reorder_ratio_recent3_avg": "Recent repeat-item ratio",
    "reorder_ratio_recent3_ratio_to_prior": "Recent repeat-item ratio relative to its historical baseline",
    "distinct_department_count_prior_to_current_avg": "Historical average number of departments per order",
    "distinct_department_count_recent3_avg": "Recent average number of departments per order",
    "distinct_department_count_recent3_delta_from_prior": "Recent department breadth changed from its historical baseline",
    "distinct_aisle_count_prior_to_current_avg": "Historical average number of aisles per order",
    "distinct_aisle_count_recent3_avg": "Recent average number of aisles per order",
    "distinct_aisle_count_recent3_delta_from_prior": "Recent aisle breadth changed from its historical baseline",
}


def get_feature_category(feature_name: str) -> str:
    """Return plain-English category for a feature name."""
    clean_name = str(feature_name).removeprefix("shap_")
    return FEATURE_CATEGORIES.get(clean_name, "Behavioral Feature")


def get_clean_feature_description(feature_name: str) -> str:
    """Return clean human-readable feature description without SHAP metadata suffixes."""
    clean_name = str(feature_name).removeprefix("shap_")
    if clean_name in FEATURE_DESCRIPTIONS:
        return FEATURE_DESCRIPTIONS[clean_name]
    return clean_name.replace("_", " ").title()


def categorize_risk_level(risk_score: float, high: float = HIGH_RISK_THRESHOLD, medium: float = MEDIUM_RISK_THRESHOLD) -> str:
    """Categorize risk score into High, Medium, or Low tier."""
    if risk_score >= high:
        return "High"
    if risk_score >= medium:
        return "Medium"
    return "Low"
