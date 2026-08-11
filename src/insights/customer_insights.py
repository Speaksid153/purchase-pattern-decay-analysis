from __future__ import annotations

import pandas as pd
from src.insights.rules import (
    HIGH_RISK_THRESHOLD,
    MEDIUM_RISK_THRESHOLD,
    categorize_risk_level,
    get_clean_feature_description,
    get_feature_category,
)


def generate_customer_insight_report(
    customer_id: int,
    latest_prediction: pd.Series,
    top_drivers: pd.DataFrame,
    customer_orders: pd.DataFrame,
) -> dict[str, str]:
    """Generate deterministic customer-level insight sections with 2 decimal place precision.

    Returns dict containing:
    - risk_summary
    - behavioral_interpretation
    - primary_risk_driver
    - primary_shap_contribution
    - protective_factor
    - protective_shap_contribution
    - shap_interpretation (combined fallback)
    - action_context

    Does NOT modify prediction data or action rules.
    """
    score = float(latest_prediction["risk_score"])
    score_pct_str = f"{score * 100:.2f}%"
    tier = categorize_risk_level(score, HIGH_RISK_THRESHOLD, MEDIUM_RISK_THRESHOLD)
    order_count = len(customer_orders)
    relative_day = int(latest_prediction.get("relative_day", 0))

    # 1. Risk Summary (2 decimal places precision)
    if tier == "High":
        risk_summary = (
            f"Customer {customer_id} is classified in the **High Risk** tier with a predicted risk score of **{score_pct_str}** "
            f"(operational threshold: $\\ge$ {HIGH_RISK_THRESHOLD * 100:.2f}%)."
        )
    elif tier == "Medium":
        risk_summary = (
            f"Customer {customer_id} is classified in the **Medium Risk** tier with a predicted risk score of **{score_pct_str}** "
            f"(operational threshold: $\\ge$ {MEDIUM_RISK_THRESHOLD * 100:.2f}%)."
        )
    else:
        risk_summary = (
            f"Customer {customer_id} maintains a **Low Risk** classification with a predicted risk score of **{score_pct_str}** "
            f"(below warning threshold of {MEDIUM_RISK_THRESHOLD * 100:.2f}%)."
        )

    # 2. Behavioral Interpretation (Why is this customer at risk / history)
    gaps = customer_orders["days_since_prior_order"].dropna()
    latest_gap = float(gaps.iloc[-1]) if not gaps.empty else 0.0
    avg_gap = float(gaps.mean()) if not gaps.empty else 0.0

    behavioral_interpretation = (
        f"Order history spans **{order_count}** recorded orders up to relative day **{relative_day}**. "
        f"Their most recent inter-purchase gap was **{latest_gap:.1f} days**, compared with a historical average of **{avg_gap:.1f} days**."
    )

    # 3. SHAP Driver Interpretation (Cleaned without redundant metadata strings)
    primary_risk_driver = "No elevated risk factor identified."
    primary_shap_contrib = "+0.000"
    protective_factor = "No protective feature factor identified."
    protective_shap_contrib = "0.000"

    parts = []
    if not top_drivers.empty:
        pos_drivers = top_drivers[top_drivers["shap_value"] > 0]
        neg_drivers = top_drivers[top_drivers["shap_value"] < 0]

        top_pos = pos_drivers.iloc[0] if not pos_drivers.empty else None
        top_neg = neg_drivers.iloc[0] if not neg_drivers.empty else None

        if top_pos is not None:
            raw_feat = str(top_pos["feature"])
            feat_cat = get_feature_category(raw_feat)
            feat_desc = get_clean_feature_description(raw_feat)
            pos_val = float(top_pos["shap_value"])
            primary_risk_driver = f"**[{feat_cat}]** {feat_desc}."
            primary_shap_contrib = f"+{pos_val:.3f}"
            parts.append(f"**Primary Risk Driver:** {primary_risk_driver} (SHAP contribution: `{primary_shap_contrib}`)")

        if top_neg is not None:
            raw_feat_neg = str(top_neg["feature"])
            feat_cat_neg = get_feature_category(raw_feat_neg)
            feat_desc_neg = get_clean_feature_description(raw_feat_neg)
            neg_val = float(top_neg["shap_value"])
            protective_factor = f"**[{feat_cat_neg}]** {feat_desc_neg}."
            protective_shap_contrib = f"{neg_val:.3f}"
            parts.append(f"**Protective Factor:** {protective_factor} (SHAP contribution: `{protective_shap_contrib}`)")

        shap_interpretation = "\n\n".join(parts) if parts else "SHAP contributions indicate balanced behavioral indicators."
    else:
        shap_interpretation = "No SHAP feature attribution data available for this customer snapshot."

    # 4. Action Context (Reusing existing deterministic ACTION_RULES recommendation without alteration)
    if not top_drivers.empty:
        action = str(top_drivers.iloc[0]["suggested_action"])
        action_context = f"**Recommended Intervention:** {action}"
    else:
        action_context = "Monitor this customer and validate behavior before initiating outreach."

    return {
        "risk_summary": risk_summary,
        "behavioral_interpretation": behavioral_interpretation,
        "primary_risk_driver": primary_risk_driver,
        "primary_shap_contribution": primary_shap_contrib,
        "protective_factor": protective_factor,
        "protective_shap_contribution": protective_shap_contrib,
        "shap_interpretation": shap_interpretation,
        "action_context": action_context,
    }
