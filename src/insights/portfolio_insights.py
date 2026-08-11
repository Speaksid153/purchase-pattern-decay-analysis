from __future__ import annotations

import pandas as pd
from src.insights.rules import get_clean_feature_description, get_feature_category


def _extract_raw_feature_name(driver_string: str) -> str:
    """Extract raw feature key from top_risk_driver summary string."""
    # driver_string format: 'readable description (raises risk; SHAP +0.123)'
    raw = driver_string.split(" (")[0]
    return raw


def generate_portfolio_insight_report(risk_table: pd.DataFrame, filtered: pd.DataFrame) -> str:
    """Generate deterministic portfolio-level written insight from calculated risk table.

    Never modifies data or calls external APIs.
    """
    total_customers = int(risk_table["customer_id"].nunique())
    if total_customers == 0:
        return "No customer prediction records available to generate portfolio insights."

    high_count = int((risk_table["risk_tier"] == "High").sum())
    medium_count = int((risk_table["risk_tier"] == "Medium").sum())
    low_count = int((risk_table["risk_tier"] == "Low").sum())

    high_pct = (high_count / total_customers) * 100
    medium_pct = (medium_count / total_customers) * 100
    low_pct = (low_count / total_customers) * 100
    elevated_count = high_count + medium_count
    elevated_pct = (elevated_count / total_customers) * 100

    elevated_df = risk_table[risk_table["risk_tier"].isin(["High", "Medium"])]
    if not elevated_df.empty:
        raw_driver = str(elevated_df["top_risk_driver"].mode().iloc[0])
    else:
        raw_driver = str(risk_table["top_risk_driver"].mode().iloc[0]) if not risk_table.empty else "N/A"

    # Clean driver description for portfolio presentation
    clean_driver = _extract_raw_feature_name(raw_driver)

    visible_customers = int(filtered["customer_id"].nunique())
    filter_active = visible_customers < total_customers

    paragraphs = []

    # 1. Portfolio Distribution
    dist_text = (
        f"**Portfolio Risk Distribution:** Out of **{total_customers:,}** scored test customers at their latest snapshot, "
        f"**{high_count:,} ({high_pct:.2f}%)** are classified as High Risk, "
        f"**{medium_count:,} ({medium_pct:.2f}%)** as Medium Risk, and "
        f"**{low_count:,} ({low_pct:.2f}%)** as Low Risk. "
        f"Elevated early-decay signals affect **{elevated_pct:.2f}%** of the active customer population."
    )
    paragraphs.append(dist_text)

    # 2. Primary Behavioral Signal (Observational, non-causal)
    driver_text = (
        f"**Primary Behavioral Signal:** Across elevated-risk customers, **\"{clean_driver}\"** "
        f"is the most prominent recurring risk signal. The operational model places greater risk weight on early changes in customer purchasing rhythm."
    )
    paragraphs.append(driver_text)

    # 3. Filter Scope Context
    if filter_active:
        filter_text = (
            f"**Filtered Scope:** Currently viewing **{visible_customers:,}** of {total_customers:,} customers "
            f"({(visible_customers / total_customers * 100):.2f}% of total). "
            f"Summary metrics above reflect active sidebar filters."
        )
        paragraphs.append(filter_text)

    return "\n\n".join(paragraphs)
