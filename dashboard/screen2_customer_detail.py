from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dashboard.ui_theme import apply_matplotlib_theme, apply_theme, render_top_navbar
from src.insights.customer_insights import generate_customer_insight_report

try:
    import streamlit as st
except ModuleNotFoundError as exc:  # pragma: no cover - runtime guidance
    raise SystemExit(
        "Streamlit is required for this dashboard screen. Install dependencies with: "
        "pip install -r requirements.txt"
    ) from exc

from dashboard.screen1_risk_table import (
    HIGH_RISK_THRESHOLD,
    MEDIUM_RISK_THRESHOLD,
    clean_feature_name,
    driver_summary,
    risk_tier,
)

PREDICTIONS_PATH = (
    ROOT
    / "data"
    / "processed"
    / "instacart"
    / "predictions"
    / "leading_xgboost_time_proxy_test_predictions.csv"
)
SHAP_PATH = (
    ROOT
    / "data"
    / "processed"
    / "instacart"
    / "predictions"
    / "leading_xgboost_time_proxy_test_shap_values.pkl"
)
ORDERS_PATH = ROOT / "data" / "processed" / "instacart" / "orders_clean.csv"

KEY_COLS = ["user_id", "order_id"]


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


def _load_data_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    predictions = pd.read_csv(PREDICTIONS_PATH)
    shap_values = pd.read_pickle(SHAP_PATH)
    orders = pd.read_csv(
        ORDERS_PATH,
        usecols=[
            "user_id",
            "order_id",
            "eval_set",
            "order_number",
            "order_dow",
            "order_hour_of_day",
            "days_since_prior_order",
            "relative_day",
        ],
    )
    return predictions, shap_values, orders


@st.cache_data(show_spinner="Loading customer detail data...")
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return _load_data_frames()


def load_api_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """API loader avoids Streamlit cache copies of the large runtime frames."""
    return _load_data_frames()


def get_top_shap_drivers(row: pd.Series, limit: int = 5) -> pd.DataFrame:
    shap_cols = [col for col in row.index if col.startswith("shap_") and col != "shap_bias"]
    drivers = (
        row[shap_cols]
        .astype(float)
        .rename(index=lambda col: clean_feature_name(col))
        .sort_values(ascending=False)
        .head(limit)
        .reset_index()
    )
    drivers.columns = ["feature", "shap_value"]
    drivers["driver_summary"] = drivers.apply(
        lambda item: driver_summary(str(item["feature"]), float(item["shap_value"])),
        axis=1,
    )
    drivers["suggested_action"] = drivers["feature"].map(ACTION_RULES).fillna(
        "Monitor this customer and validate the driver before discounting."
    )
    return drivers


def customer_insight(customer_id: int, latest_prediction: pd.Series, top_driver: pd.Series) -> str:
    score = float(latest_prediction["risk_score"])
    tier = risk_tier(score, HIGH_RISK_THRESHOLD, MEDIUM_RISK_THRESHOLD)
    driver_text = str(top_driver["driver_summary"])
    action = str(top_driver["suggested_action"])
    return (
        f"Customer {customer_id} is currently classified as {tier} risk "
        f"with a risk score of {score:.2%}. Main driver: {driver_text}. "
        f"Recommended action: {action}"
    )


def plot_risk_trend(customer_predictions: pd.DataFrame) -> plt.Figure:
    apply_matplotlib_theme()
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(
        customer_predictions["relative_day"],
        customer_predictions["risk_score"],
        marker="o",
        linewidth=2,
        color="#2563eb",
    )
    ax.axhline(HIGH_RISK_THRESHOLD, color="#ba1a1a", linestyle="--", linewidth=1.5, label="High threshold")
    ax.axhline(MEDIUM_RISK_THRESHOLD, color="#d97706", linestyle="--", linewidth=1.5, label="Medium threshold")
    ax.set_title("Risk Score Over Customer Timeline", fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("Relative day", fontsize=11)
    ax.set_ylabel("Risk score", fontsize=11)
    ax.set_ylim(0, 1)
    ax.grid(alpha=0.3, color="#c4c7c7")
    ax.legend(loc="best", frameon=True, facecolor="#ffffff", edgecolor="#c4c7c7")
    fig.tight_layout()
    return fig


def plot_purchase_history(customer_orders: pd.DataFrame) -> plt.Figure:
    apply_matplotlib_theme()
    fig, ax = plt.subplots(figsize=(8, 3.6))
    orders = customer_orders[customer_orders["days_since_prior_order"].notna()].copy()
    if orders.empty:
        ax.text(0.5, 0.5, "No prior-gap history available", ha="center", va="center")
        ax.axis("off")
    else:
        ax.plot(
            orders["order_number"],
            orders["days_since_prior_order"],
            marker="o",
            linewidth=2,
            color="#266b41",
        )
        ax.set_title("Purchase Gap History", fontsize=13, fontweight="bold", pad=10)
        ax.set_xlabel("Order number", fontsize=11)
        ax.set_ylabel("Days since prior order", fontsize=11)
        ax.grid(alpha=0.3, color="#c4c7c7")
    fig.tight_layout()
    return fig


def plot_shap_drivers(top_drivers: pd.DataFrame) -> plt.Figure:
    apply_matplotlib_theme()
    fig, ax = plt.subplots(figsize=(8, 3.6))
    display = top_drivers.iloc[::-1]
    labels = display["feature"].str.replace("_", " ", regex=False)
    colors = np.where(display["shap_value"] >= 0, "#ba1a1a", "#266b41")
    ax.barh(labels, display["shap_value"], color=colors, height=0.55)
    ax.axvline(0, color="#747878", linewidth=1)
    ax.set_title("Top SHAP Risk Drivers", fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("Contribution to risk", fontsize=11)
    ax.grid(alpha=0.3, color="#c4c7c7")
    fig.tight_layout()
    return fig


def get_prioritized_customers(predictions: pd.DataFrame) -> list[tuple[int, str]]:
    """Return list of (user_id, label) sorted by latest risk score descending."""
    latest_scores = (
        predictions.sort_values(["user_id", "relative_day", "order_id"], kind="mergesort")
        .groupby("user_id", as_index=False)
        .tail(1)
        .sort_values("risk_score", ascending=False)
    )
    result = []
    for _, row in latest_scores.iterrows():
        uid = int(row["user_id"])
        score = float(row["risk_score"])
        tier = risk_tier(score, HIGH_RISK_THRESHOLD, MEDIUM_RISK_THRESHOLD)
        label = f"Customer {uid} | {tier} Risk ({score:.1%})"
        result.append((uid, label))
    return result


def render(customer_id: int | None = None) -> None:
    st.error("This Streamlit screen is retired. Use the React dashboard at http://127.0.0.1:5173.")
    return
    apply_theme()
    render_top_navbar("Customer Detail")

    predictions, shap_values, orders = load_data()
    prioritized = get_prioritized_customers(predictions)
    available_customers = [uid for uid, _ in prioritized]

    if customer_id is None:
        customer_id = available_customers[0]

    customer_predictions = predictions[predictions["user_id"] == customer_id].sort_values(
        ["relative_day", "order_id"],
        kind="mergesort",
    )
    customer_orders = orders[orders["user_id"] == customer_id].sort_values("order_number", kind="mergesort")

    if customer_predictions.empty:
        st.warning(
            f"Customer {customer_id} is not in the focused leading-XGBoost test scoring population. "
            f"Try one of these available IDs: {available_customers[:5]}"
        )
        return

    latest_prediction = customer_predictions.iloc[-1]
    latest_shap = shap_values[
        (shap_values["user_id"] == latest_prediction["user_id"])
        & (shap_values["order_id"] == latest_prediction["order_id"])
    ]
    if latest_shap.empty:
        st.warning("Prediction exists, but SHAP detail is missing for the latest scored snapshot.")
        return

    top_drivers = get_top_shap_drivers(latest_shap.iloc[0])
    top_driver = top_drivers.iloc[0]
    score_val = float(latest_prediction["risk_score"])
    tier = risk_tier(score_val, HIGH_RISK_THRESHOLD, MEDIUM_RISK_THRESHOLD)

    # Risk badge formatting
    if tier == "High":
        badge_style = "bg-[#ffdad6] text-[#93000a] border-[#ffb4ab]"
        badge_icon = "warning"
        score_color = "text-[#ba1a1a]"
    elif tier == "Medium":
        badge_style = "bg-[#ffe1a8] text-[#5e4200] border-[#e5b261]"
        badge_icon = "error"
        score_color = "text-[#d97706]"
    else:
        badge_style = "bg-[#e2f5e9] text-[#02522b] border-[#abf3bd]"
        badge_icon = "check_circle"
        score_color = "text-[#266b41]"

    action_text = str(top_driver["suggested_action"])

    # HEADER & HERO BENTO GRID
    header_html = f"""
    <div class="grid grid-cols-1 md:grid-cols-12 gap-[24px] mb-[24px]">
        <!-- Profile Header (Left 7 cols) -->
        <div class="md:col-span-7 bg-[#ffffff] border border-[#c4c7c7] rounded-lg p-[24px] flex flex-col justify-between">
            <div class="flex items-center justify-between mb-4">
                <span class="font-label-sm text-[12px] text-[#444748] uppercase tracking-wider font-semibold">Customer Risk Detail</span>
                <span class="font-label-sm text-[12px] text-[#747878]">{len(customer_predictions)} Scored Snapshots</span>
            </div>
            <div class="flex items-end justify-between">
                <div>
                    <h1 class="font-headline-lg text-[32px] font-bold text-[#000000] mb-2 tracking-tight">Customer {customer_id}</h1>
                    <div class="flex items-center gap-3">
                        <span class="font-label-sm text-[12px] text-[#444748]">Current Risk Status:</span>
                        <span class="{badge_style} font-label-sm text-[12px] px-3 py-1 rounded-full flex items-center gap-1 font-semibold border">
                            <span class="material-symbols-outlined text-[14px]">{badge_icon}</span> {tier} Risk
                        </span>
                    </div>
                </div>
                <div class="flex flex-col items-end">
                    <span class="font-label-sm text-[12px] text-[#444748] mb-1 font-medium">Predictive Risk Score</span>
                    <span class="font-display-tabular text-[36px] font-bold {score_color}">{score_val:.2%}</span>
                </div>
            </div>
        </div>

        <!-- Recommended Intervention (Right 5 cols) -->
        <div class="md:col-span-5 bg-[#ffdad6] border border-[#ffb4ab] rounded-lg p-[24px] flex flex-col justify-center relative overflow-hidden">
            <div class="flex items-center gap-2 mb-3 z-10">
                <span class="material-symbols-outlined text-[#93000a] text-[22px]">assignment_late</span>
                <h2 class="font-headline-md text-[18px] font-bold text-[#93000a]">Recommended Intervention</h2>
            </div>
            <p class="font-body-md text-[14px] text-[#93000a] z-10 leading-relaxed font-medium">
                {action_text}
            </p>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

    # DETAILED BEHAVIORAL ANALYSIS
    ci_report = generate_customer_insight_report(customer_id, latest_prediction, top_drivers, customer_orders)
    
    analysis_html = f"""
    <div class="bg-[#ffffff] border border-[#c4c7c7] rounded-lg p-[24px] mb-[24px]">
        <h3 class="font-headline-md text-[18px] font-bold text-[#000000] mb-3">Detailed Behavioral Analysis & Attribution</h3>
        <div class="space-y-3 text-[14px] text-[#1a1c1b] leading-relaxed">
            <p>{ci_report['risk_summary']}</p>
            <p><strong class="text-[#000000]">Why is this customer at risk?</strong> {ci_report['behavioral_interpretation']}</p>
            <div class="bg-[#f4f3f1] p-[16px] rounded border border-[#e3e2e0]">
                {ci_report['shap_interpretation'].replace('\n\n', '<br/>')}
            </div>
            <p><strong class="text-[#000000]">Action Context:</strong> {ci_report['action_context']}</p>
        </div>
        <div class="mt-4 pt-3 border-t border-[#e3e2e0]">
            <span class="font-label-sm text-[12px] text-[#747878] flex items-center gap-1 font-medium">
                <span class="material-symbols-outlined text-[14px]">policy</span> Deterministic analysis · No AI inference
            </span>
        </div>
    </div>
    """
    st.markdown(analysis_html, unsafe_allow_html=True)

    # CHARTS AREA
    left, right = st.columns(2)
    with left:
        st.pyplot(plot_risk_trend(customer_predictions), clear_figure=True)
    with right:
        st.pyplot(plot_purchase_history(customer_orders), clear_figure=True)

    st.pyplot(plot_shap_drivers(top_drivers), clear_figure=True)

    st.subheader("Driver-Based Actions")
    st.dataframe(
        top_drivers[["driver_summary", "suggested_action", "shap_value"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "driver_summary": "Driver",
            "suggested_action": "Suggested action",
            "shap_value": st.column_config.NumberColumn("SHAP value", format="%.3f"),
        },
    )


def main() -> None:
    st.set_page_config(page_title="Customer Detail", layout="wide")
    predictions, _, _ = load_data()
    prioritized = get_prioritized_customers(predictions)

    st.sidebar.header("Customer Selector")
    label_to_id = {label: uid for uid, label in prioritized}
    labels = list(label_to_id.keys())

    selected_label = st.sidebar.selectbox(
        "Select Customer (High Risk First)",
        labels,
        index=0,
        help="Customers are sorted by risk score (High Risk first). Type to search.",
    )
    selected_id = label_to_id[selected_label]
    render(selected_id)


if __name__ == "__main__":
    main()
