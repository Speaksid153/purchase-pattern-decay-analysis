from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.insights.rules import get_clean_feature_description, get_feature_category

ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS_PATH = ROOT / "data/processed/instacart/predictions/leading_xgboost_time_proxy_test_predictions.csv"
SHAP_PATH = ROOT / "data/processed/instacart/predictions/leading_xgboost_time_proxy_test_shap_values.pkl"
ORDERS_PATH = ROOT / "data/processed/instacart/orders_clean.csv"
MODEL_REPORT_PATH = ROOT / "reports/modeling/instacart/phase4_leading_xgboost_report.json"
HIGH_RISK_THRESHOLD = 0.70
MEDIUM_RISK_THRESHOLD = 0.45

ACTION_RULES = {
    "current_gap_ratio_to_historical_median": "Send a personalized reorder reminder with a short expiry window.",
    "current_gap_gt_1_5x_historical_median": "Trigger a light-touch reminder before the gap grows further.",
    "current_gap_gt_2x_historical_median": "Prioritize immediate recovery outreach or a targeted incentive.",
    "latest_gap_ratio_to_prior_avg": "Use cadence-based replenishment messaging.",
    "latest_gap_ratio_to_previous_gap": "Prompt a reorder because the latest gap accelerated sharply.",
    "gap_acceleration_1_5x_flag": "Use urgency messaging tied to the customer's usual reorder rhythm.",
    "gap_slope_last3": "Send a win-back sequence because gaps are trending upward.",
    "purchase_frequency_slope_last3": "Use frequency recovery messaging and reorder shortcuts.",
    "item_count_recent3_ratio_to_prior": "Recommend frequently bought items or bundles to rebuild basket size.",
    "item_count_recent3_delta_from_prior": "Offer basket-building recommendations.",
    "basket_size_decay_flag": "Use cart expansion offers or relevant add-on recommendations.",
    "reorder_ratio_recent3_delta_from_prior": "Surface previously reordered items to restore habit.",
    "reorder_ratio_slope_last3": "Use personalized replenishment prompts for repeat items.",
    "reorder_behavior_decay_flag": "Prioritize reorder convenience: one-click repeat cart or reminder.",
    "distinct_department_count_recent3_ratio_to_prior": "Recommend adjacent categories the customer used to buy.",
    "distinct_aisle_count_recent3_ratio_to_prior": "Use discovery recommendations to widen the basket again.",
    "category_diversity_narrowing_flag": "Show category rediscovery prompts.",
    "hour_distance_from_prior_pattern": "Monitor timing drift; avoid aggressive discounting based only on timing.",
    "dow_distance_from_prior_pattern": "Monitor schedule drift; use reminder timing tests.",
    "time_consistency_decay_flag": "Test reminders around the customer's old preferred order window.",
}


def risk_band(score: float) -> str:
    if score >= HIGH_RISK_THRESHOLD:
        return "High"
    if score >= MEDIUM_RISK_THRESHOLD:
        return "Medium"
    return "Low"


def model_metrics_payload() -> dict:
    report = json.loads(MODEL_REPORT_PATH.read_text(encoding="utf-8"))
    metrics, timing = report["test_metrics"], report["timing_metric"]
    return {
        "modelName": "Temporally robust leading XGBoost (relative-time proxy)",
        "rocAuc": round(float(metrics["roc_auc"]), 4),
        "prAuc": round(float(metrics["pr_auc"]), 4),
        "evaluationThreshold": round(float(metrics["threshold"]), 4),
        "precisionAtEvaluationThreshold": round(float(metrics["precision_at_threshold"]), 4),
        "recallAtEvaluationThreshold": round(float(metrics["recall_at_threshold"]), 4),
        "medianLeadTimeDays": round(float(timing["days_before_decay_threshold_summary"]["median"]), 1),
        "correctlyFlaggedUsers": int(timing["correctly_flagged_users"]),
        "positiveEventUsers": int(timing["positive_event_users"]),
        "methodology": "Selected across two rolling user-lifecycle development folds, retrained on train plus validation, and evaluated once on an untouched final 15% user cohort. The evaluation cutoff is development-derived; the score is not a calibrated probability or a calendar-time churn forecast.",
    }


def _drivers_from_values(values: np.ndarray, features: list[str]) -> tuple[list[dict], dict, dict, str]:
    """Build driver payloads without allocating a pandas Series per customer."""
    positive = np.flatnonzero(values > 0)
    negative = np.flatnonzero(values < 0)
    positive = positive[np.argsort(-values[positive], kind="stable")]
    negative = negative[np.argsort(values[negative], kind="stable")]
    primary_feature = features[int(positive[0])] if positive.size else "No positive feature contribution"
    primary_value = float(values[positive[0]]) if positive.size else 0.0
    protective_feature = features[int(negative[0])] if negative.size else "No feature reduced the model score"
    protective_value = float(values[negative[0]]) if negative.size else 0.0
    displayed = [
        {"feature": feature, "cleanDescription": get_clean_feature_description(feature), "category": get_feature_category(feature), "shapValue": round(float(values[index]), 4), "suggestedAction": ACTION_RULES.get(feature, "Validate this signal before offering an incentive.")}
        for index in positive[:5]
        for feature in [features[int(index)]]
    ]
    return (
        displayed,
        {"feature": get_clean_feature_description(str(primary_feature)), "category": get_feature_category(str(primary_feature)), "shapValue": round(primary_value, 4)},
        {"feature": get_clean_feature_description(str(protective_feature)), "category": get_feature_category(str(protective_feature)), "shapValue": round(protective_value, 4)},
        str(primary_feature),
    )


def _drivers(shap_row: pd.Series) -> tuple[list[dict], dict, dict, str]:
    columns = [c for c in shap_row.index if c.startswith("shap_") and c != "shap_bias"]
    return _drivers_from_values(
        shap_row[columns].to_numpy(dtype=float),
        [column.removeprefix("shap_") for column in columns],
    )


def orders_through_snapshot(orders_group: pd.DataFrame, latest_order_id: int) -> pd.DataFrame:
    """Return one customer's order history through the scored order.

    Prediction and SHAP rows are keyed to a specific order.  Using orders after
    that point mixes future behavior into the evidence shown for the score.
    """
    matches = orders_group.index[orders_group["order_id"].eq(latest_order_id)]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one scored order {latest_order_id}; found {len(matches)}"
        )
    scored_order_number = int(orders_group.loc[matches[0], "order_number"])
    return orders_group[orders_group["order_number"].le(scored_order_number)].copy()


def snapshot_gap_metrics(snapshot_orders: pd.DataFrame) -> tuple[float, float]:
    """Return the scored gap and its prior-only historical baseline."""
    observed_gaps = snapshot_orders["days_since_prior_order"].dropna()
    historical_gaps = snapshot_orders.iloc[:-1]["days_since_prior_order"].dropna()
    latest_gap = round(float(observed_gaps.iloc[-1]), 1) if not observed_gaps.empty else 0.0
    historical_average = round(float(historical_gaps.mean()), 1) if not historical_gaps.empty else 0.0
    return latest_gap, historical_average


def raw_customer_records() -> tuple[list[dict], dict[int, dict]]:
    """Materialize the old raw-artifact behavior once, for cache building/audit only."""
    predictions = pd.read_csv(PREDICTIONS_PATH).sort_values(["user_id", "relative_day", "order_id"], kind="mergesort")
    latest = predictions.groupby("user_id", as_index=False).tail(1)[["user_id", "order_id"]]
    # Join once instead of doing 25,718 expensive MultiIndex lookups.
    latest_shap = latest.merge(pd.read_pickle(SHAP_PATH), on=["user_id", "order_id"], how="left", validate="one_to_one")
    if latest_shap.filter(regex=r"^shap_").isna().all(axis=1).any():
        raise ValueError("One or more latest prediction rows have no SHAP detail")
    shap_columns = [column for column in latest_shap.columns if column.startswith("shap_") and column != "shap_bias"]
    shap_features = [column.removeprefix("shap_") for column in shap_columns]
    driver_by_customer = {
        int(customer_id): _drivers_from_values(values, shap_features)
        for customer_id, values in zip(
            latest_shap["user_id"].to_numpy(),
            latest_shap[shap_columns].to_numpy(dtype=float, copy=False),
            strict=True,
        )
    }
    orders = pd.read_csv(
        ORDERS_PATH,
        usecols=["order_id", "user_id", "order_number", "days_since_prior_order"],
    )
    order_groups = {int(uid): group.sort_values("order_number", kind="mergesort") for uid, group in orders.groupby("user_id", sort=False)}
    prediction_groups = {int(uid): group for uid, group in predictions.groupby("user_id", sort=False)}
    portfolio, details = [], {}
    for customer_id, pred_group in prediction_groups.items():
        latest = pred_group.iloc[-1]
        drivers, primary, protective, primary_feature = driver_by_customer[customer_id]
        orders_group = order_groups.get(customer_id, pd.DataFrame(columns=orders.columns))
        snapshot_orders = orders_through_snapshot(orders_group, int(latest["order_id"]))
        latest_gap, historical_average = snapshot_gap_metrics(snapshot_orders)
        score, band = float(latest["risk_score"]), risk_band(float(latest["risk_score"]))
        intervention = ACTION_RULES.get(primary_feature, "Validate this signal before offering an incentive.")
        detail = {
            "id": str(customer_id), "riskScore": round(score, 4), "riskTier": band,
            "lastPurchaseDays": latest_gap,
            "lastPurchaseDate": f"Relative Day {int(latest['relative_day'])}",
            "historicAvgGap": historical_average,
            "orderVolume": len(snapshot_orders), "primaryRiskDriver": primary, "protectiveFactor": protective,
            "timelineHistory": [{"day": int(row.relative_day), "score": round(float(row.risk_score), 4)} for row in pred_group.itertuples()],
            "shapDrivers": drivers, "recommendedIntervention": intervention,
            "insightReport": {"risk_summary": f"Customer {customer_id} is in the {band} operational review band with a model score of {score:.3f}. Risk bands are segmentation rules applied to the score, not calibrated probabilities."},
            "orderHistory": [{"orderNumber": int(row.order_number), "daysSincePrior": round(float(row.days_since_prior_order), 1) if pd.notna(row.days_since_prior_order) else None} for row in snapshot_orders.itertuples()],
        }
        details[customer_id] = detail
        portfolio.append({"customer_id": customer_id, "score": round(score, 4), "risk_band": band, "top_driver": get_clean_feature_description(primary_feature), "latest_order_id": int(latest["order_id"]), "relative_day": int(latest["relative_day"]), "last_purchase_days": detail["lastPurchaseDays"], "historic_avg_gap": detail["historicAvgGap"], "order_volume": detail["orderVolume"]})
    portfolio.sort(key=lambda row: (-row["score"], row["customer_id"]))
    return portfolio, details
