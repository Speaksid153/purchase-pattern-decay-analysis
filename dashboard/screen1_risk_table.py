from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

try:
    import streamlit as st
except ModuleNotFoundError as exc:  # pragma: no cover - runtime guidance
    raise SystemExit(
        "Streamlit is required for this dashboard screen. Install dependencies with: "
        "pip install -r requirements.txt"
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dashboard.ui_theme import apply_theme, render_top_navbar
from src.insights.portfolio_insights import generate_portfolio_insight_report

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

KEY_COLS = ["user_id", "order_id"]
_api_preloaded_frames: tuple[pd.DataFrame, pd.DataFrame] | None = None


def set_api_preloaded_frames(predictions: pd.DataFrame, shap_values: pd.DataFrame) -> None:
    """Reuse API-owned frames so its portfolio table does not re-read both artifacts."""
    global _api_preloaded_frames
    _api_preloaded_frames = (predictions, shap_values)
HIGH_RISK_THRESHOLD = 0.70
MEDIUM_RISK_THRESHOLD = 0.45


FEATURE_LABELS = {
    "current_gap_ratio_to_historical_median": "current purchase gap is high vs normal cadence",
    "current_gap_gt_1_5x_historical_median": "current gap crossed 1.5x normal cadence",
    "current_gap_gt_2x_historical_median": "current gap crossed 2x normal cadence",
    "latest_gap_ratio_to_prior_avg": "latest gap is high vs prior average",
    "latest_gap_ratio_to_previous_gap": "latest gap accelerated vs previous gap",
    "gap_acceleration_1_5x_flag": "gap acceleration crossed warning threshold",
    "gap_slope_last3": "purchase gaps are trending upward",
    "purchase_frequency_slope_last3": "purchase frequency is weakening",
    "item_count_recent3_ratio_to_prior": "recent basket size is shrinking",
    "item_count_recent3_delta_from_prior": "recent basket item count is down",
    "basket_size_decay_flag": "basket size decay flag is active",
    "reorder_ratio_recent3_delta_from_prior": "reorder habit is weakening",
    "reorder_ratio_slope_last3": "reorder behavior is trending down",
    "reorder_behavior_decay_flag": "reorder behavior decay flag is active",
    "distinct_department_count_recent3_ratio_to_prior": "department diversity is narrowing",
    "distinct_aisle_count_recent3_ratio_to_prior": "aisle diversity is narrowing",
    "category_diversity_narrowing_flag": "category diversity narrowing flag is active",
    "hour_distance_from_prior_pattern": "order hour shifted from usual pattern",
    "dow_distance_from_prior_pattern": "order day shifted from usual pattern",
    "time_consistency_decay_flag": "ordering time consistency is weakening",
    "history_reliability_score": "longer behavior history supports the warning",
    "known_gap_count_feature": "more observed gaps support the warning",
    "behavior_orders_to_date": "customer order-history depth affects risk",
}


def risk_tier(score: float, high: float, medium: float) -> str:
    if score >= high:
        return "High"
    if score >= medium:
        return "Medium"
    return "Low"


def clean_feature_name(shap_column: str) -> str:
    return shap_column.removeprefix("shap_")


def driver_summary(feature: str, contribution: float) -> str:
    readable = FEATURE_LABELS.get(feature, feature.replace("_", " "))
    direction = "raises" if contribution >= 0 else "reduces"
    return f"{readable} ({direction} risk; SHAP {contribution:+.3f})"


@st.cache_data(show_spinner="Loading Phase 4 predictions and SHAP values...")
def load_customer_risk_table(high_threshold: float, medium_threshold: float) -> pd.DataFrame:
    if _api_preloaded_frames is None:
        predictions = pd.read_csv(PREDICTIONS_PATH)
        shap_values = pd.read_pickle(SHAP_PATH)
    else:
        predictions, shap_values = _api_preloaded_frames

    required_prediction_cols = {
        "user_id",
        "order_id",
        "relative_day",
        "risk_score",
    }
    missing_predictions = required_prediction_cols - set(predictions.columns)
    if missing_predictions:
        raise ValueError(f"Prediction file missing columns: {sorted(missing_predictions)}")

    missing_shap_keys = set(KEY_COLS) - set(shap_values.columns)
    if missing_shap_keys:
        raise ValueError(f"SHAP file missing key columns: {sorted(missing_shap_keys)}")

    shap_cols = [col for col in shap_values.columns if col.startswith("shap_") and col != "shap_bias"]
    if not shap_cols:
        raise ValueError("No SHAP feature columns found")

    # The portfolio is one latest snapshot per customer. Select those snapshots before
    # joining SHAP values; joining every historical order is equivalent but needlessly
    # materializes a much larger intermediate frame.
    latest = (
        predictions.sort_values(["user_id", "relative_day", "order_id"], kind="mergesort")
        .groupby("user_id", as_index=False)
        .tail(1)
        .copy()
    )
    latest = latest.merge(shap_values[[*KEY_COLS, *shap_cols]], on=KEY_COLS, how="left", validate="one_to_one")
    if latest[shap_cols].isna().all(axis=1).any():
        missing_rows = int(latest[shap_cols].isna().all(axis=1).sum())
        raise ValueError(f"{missing_rows:,} prediction rows have no SHAP values")

    shap_array = latest[shap_cols].to_numpy()
    positive_shap = np.where(shap_array > 0, shap_array, -np.inf)
    has_positive_driver = np.isfinite(positive_shap).any(axis=1)
    positive_idx = positive_shap.argmax(axis=1)
    absolute_idx = np.abs(shap_array).argmax(axis=1)
    top_idx = np.where(has_positive_driver, positive_idx, absolute_idx)
    top_features = [clean_feature_name(shap_cols[i]) for i in top_idx]
    top_contributions = shap_array[np.arange(shap_array.shape[0]), top_idx]

    latest["top_risk_driver"] = [
        driver_summary(feature, contribution)
        for feature, contribution in zip(top_features, top_contributions, strict=True)
    ]

    latest["risk_tier"] = latest["risk_score"].map(
        lambda score: risk_tier(float(score), high_threshold, medium_threshold)
    )
    latest["customer_id"] = latest["user_id"]
    latest["churn_risk_score"] = latest["risk_score"].clip(0, 1)

    columns = [
        "customer_id",
        "churn_risk_score",
        "risk_tier",
        "top_risk_driver",
        "order_id",
        "relative_day",
    ]
    if "early_decay_label" in latest.columns:
        columns.append("early_decay_label")
    if "flagged_at_threshold" in latest.columns:
        columns.append("flagged_at_threshold")

    return latest[columns].sort_values("churn_risk_score", ascending=False).reset_index(drop=True)


def render() -> None:
    st.error("This Streamlit screen is retired. Use the React dashboard at http://127.0.0.1:5173.")
    return
    apply_theme()
    render_top_navbar("Portfolio Risk")

    with st.sidebar:
        st.header("Filters")
        high_threshold = st.slider("High risk threshold", 0.50, 0.95, HIGH_RISK_THRESHOLD, 0.01)
        medium_threshold = st.slider("Medium risk threshold", 0.10, high_threshold, MEDIUM_RISK_THRESHOLD, 0.01)
        tiers = st.multiselect("Risk tiers", ["High", "Medium", "Low"], default=["High", "Medium", "Low"])
        score_range = st.slider("Risk score range", 0.0, 1.0, (0.0, 1.0), 0.01)
        customer_search = st.text_input("Customer ID contains")
        max_rows = st.number_input("Rows to display", min_value=100, max_value=100_000, value=25_000, step=100)

    risk_table = load_customer_risk_table(high_threshold, medium_threshold)

    filtered = risk_table[
        risk_table["risk_tier"].isin(tiers)
        & risk_table["churn_risk_score"].between(score_range[0], score_range[1], inclusive="both")
    ].copy()
    if customer_search.strip():
        filtered = filtered[filtered["customer_id"].astype(str).str.contains(customer_search.strip(), regex=False)]

    total_customers = risk_table["customer_id"].nunique()
    visible_customers = filtered["customer_id"].nunique()
    high_count = int((risk_table["risk_tier"] == "High").sum())
    medium_count = int((risk_table["risk_tier"] == "Medium").sum())
    low_count = int((risk_table["risk_tier"] == "Low").sum())

    high_pct = (high_count / total_customers * 100) if total_customers else 0.0
    medium_pct = (medium_count / total_customers * 100) if total_customers else 0.0
    low_pct = (low_count / total_customers * 100) if total_customers else 0.0
    elevated_pct = ((high_count + medium_count) / total_customers * 100) if total_customers else 0.0

    # Determine dominant risk driver deterministically across elevated risk customers
    elevated = risk_table[risk_table["risk_tier"].isin(["High", "Medium"])]
    if not elevated.empty:
        dominant_driver = elevated["top_risk_driver"].mode().iloc[0]
    else:
        dominant_driver = risk_table["top_risk_driver"].mode().iloc[0] if not risk_table.empty else "N/A"

    # 1. METRIC STRIP (5 Cards matching design system)
    metric_strip_html = f"""
    <section class="grid grid-cols-2 md:grid-cols-5 gap-[16px] mb-[24px]">
        <div class="bg-[#ffffff] p-[16px] rounded border border-[#c4c7c7] flex flex-col gap-2 relative overflow-hidden group hover:border-[#747878] transition-colors duration-200">
            <div class="absolute top-0 left-0 w-1 h-full bg-[#ba1a1a]"></div>
            <span class="font-label-sm text-[12px] font-medium text-[#444748] uppercase tracking-wider pl-2">High Risk</span>
            <div class="flex items-baseline gap-2 pl-2">
                <span class="font-display-tabular text-[32px] font-semibold text-[#000000]">{high_count:,}</span>
                <span class="text-[12px] font-medium text-[#ba1a1a]">{high_pct:.1f}%</span>
            </div>
        </div>
        <div class="bg-[#ffffff] p-[16px] rounded border border-[#c4c7c7] flex flex-col gap-2 relative overflow-hidden group hover:border-[#747878] transition-colors duration-200">
            <div class="absolute top-0 left-0 w-1 h-full bg-[#E5B261]"></div>
            <span class="font-label-sm text-[12px] font-medium text-[#444748] uppercase tracking-wider pl-2">Medium Risk</span>
            <div class="flex items-baseline gap-2 pl-2">
                <span class="font-display-tabular text-[32px] font-semibold text-[#000000]">{medium_count:,}</span>
                <span class="text-[12px] font-medium text-[#d97706]">{medium_pct:.1f}%</span>
            </div>
        </div>
        <div class="bg-[#ffffff] p-[16px] rounded border border-[#c4c7c7] flex flex-col gap-2 relative overflow-hidden group hover:border-[#747878] transition-colors duration-200">
            <div class="absolute top-0 left-0 w-1 h-full bg-[#266b41]"></div>
            <span class="font-label-sm text-[12px] font-medium text-[#444748] uppercase tracking-wider pl-2">Low Risk</span>
            <div class="flex items-baseline gap-2 pl-2">
                <span class="font-display-tabular text-[32px] font-semibold text-[#000000]">{low_count:,}</span>
                <span class="text-[12px] font-medium text-[#266b41]">{low_pct:.1f}%</span>
            </div>
        </div>
        <div class="bg-[#ffffff] p-[16px] rounded border border-[#c4c7c7] flex flex-col gap-2 relative overflow-hidden group hover:border-[#747878] transition-colors duration-200">
            <span class="font-label-sm text-[12px] font-medium text-[#444748] uppercase tracking-wider">Total Customers</span>
            <div class="flex items-baseline gap-2">
                <span class="font-display-tabular text-[32px] font-semibold text-[#000000]">{total_customers:,}</span>
            </div>
        </div>
        <div class="bg-[#ffffff] p-[16px] rounded border border-[#c4c7c7] flex flex-col gap-2 relative overflow-hidden group hover:border-[#747878] transition-colors duration-200">
            <span class="font-label-sm text-[12px] font-medium text-[#444748] uppercase tracking-wider">Visible (Filtered)</span>
            <div class="flex items-baseline gap-2">
                <span class="font-display-tabular text-[32px] font-semibold text-[#000000]">{visible_customers:,}</span>
                <span class="text-[12px] font-medium text-[#444748]">{elevated_pct:.1f}% elevated</span>
            </div>
        </div>
    </section>
    """
    st.markdown(metric_strip_html, unsafe_allow_html=True)

    # 2. DOMINANT SIGNAL & INSIGHT BENTO
    portfolio_insight_text = generate_portfolio_insight_report(risk_table, filtered)
    
    bento_html = f"""
    <section class="grid grid-cols-1 md:grid-cols-3 gap-[24px] mb-[24px]">
        <div class="md:col-span-2 bg-[#ffffff] border border-[#c4c7c7] rounded p-[24px] flex flex-col justify-center">
            <span class="font-label-sm text-[12px] text-[#444748] uppercase tracking-wider mb-2 font-semibold">PRIMARY BEHAVIORAL SIGNAL</span>
            <p class="font-headline-lg text-[22px] font-bold text-[#000000] leading-snug">{dominant_driver}</p>
        </div>
        <div class="bg-[#ffffff] border border-[#c4c7c7] rounded flex flex-col h-full">
            <div class="p-[24px] flex-grow flex flex-col gap-2">
                <span class="font-label-sm text-[12px] text-[#444748] uppercase tracking-wider font-semibold">PORTFOLIO INSIGHT</span>
                <div class="text-[14px] text-[#1a1c1b] leading-relaxed">
                    {portfolio_insight_text.replace('\n\n', '<br/><br/>')}
                </div>
            </div>
            <div class="border-t border-[#c4c7c7] p-[12px] px-[24px] bg-[#f4f3f1]">
                <span class="font-label-sm text-[12px] text-[#747878] flex items-center gap-1 font-medium">
                    <span class="material-symbols-outlined text-[14px]">policy</span> Deterministic analysis · No AI inference
                </span>
            </div>
        </div>
    </section>
    """
    st.markdown(bento_html, unsafe_allow_html=True)

    # 3. DATA AREA & ACTIONS
    csv_data = filtered.head(int(max_rows)).to_csv(index=False).encode("utf-8")
    
    st.subheader("Customer Risk Table")
    
    st.download_button(
        label="Download Filtered Risk Table (CSV)",
        data=csv_data,
        file_name="customer_churn_risk_table.csv",
        mime="text/csv",
        help="Export the current filtered customer risk table to CSV",
    )

    st.dataframe(
        filtered.head(int(max_rows)),
        use_container_width=True,
        hide_index=True,
        column_config={
            "customer_id": "Customer ID",
            "churn_risk_score": st.column_config.ProgressColumn(
                "Churn risk score",
                min_value=0.0,
                max_value=1.0,
                format="%.3f",
            ),
            "risk_tier": "Risk tier",
            "top_risk_driver": "Top risk driver",
            "relative_day": "Relative day",
        },
    )

    st.caption(
        "One row per customer, using the latest scored test snapshot from the focused leading-XGBoost model. "
        "Table columns are sortable in the UI; filters are in the sidebar."
    )


def main() -> None:
    st.set_page_config(page_title="Customer Churn Risk Table", layout="wide")
    render()


if __name__ == "__main__":
    main()
