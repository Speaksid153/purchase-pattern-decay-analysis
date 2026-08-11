from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "instacart"
REPORT = ROOT / "reports" / "eda" / "instacart"
PLOTS = REPORT / "plots"


def ensure_dirs() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    PLOTS.mkdir(parents=True, exist_ok=True)


def save_hist(values: pd.Series, title: str, xlabel: str, path: Path, *, bins: int = 50, logy: bool = False) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(values.dropna(), bins=bins, color="#3b6ea8", edgecolor="white")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Count")
    if logy:
        ax.set_yscale("log")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def save_bar(series: pd.Series, title: str, xlabel: str, ylabel: str, path: Path, *, rotate: int = 0) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    series.plot(kind="bar", ax=ax, color="#3b6ea8")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=rotate)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def save_boxplot_by_label(df: pd.DataFrame, value_col: str, label_col: str, title: str, ylabel: str, path: Path) -> None:
    plot_df = df[[value_col, label_col]].dropna()
    groups = [
        plot_df.loc[~plot_df[label_col], value_col].clip(lower=plot_df[value_col].quantile(0.01), upper=plot_df[value_col].quantile(0.99)),
        plot_df.loc[plot_df[label_col], value_col].clip(lower=plot_df[value_col].quantile(0.01), upper=plot_df[value_col].quantile(0.99)),
    ]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.boxplot(groups, tick_labels=["No future 30d gap", "Future 30d gap"], showfliers=False)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def pct(x: float) -> str:
    return f"{x:.2%}"


def describe(series: pd.Series) -> dict[str, float]:
    s = series.dropna()
    if s.empty:
        return {}
    return {
        "count": int(s.shape[0]),
        "mean": float(s.mean()),
        "median": float(s.median()),
        "p25": float(s.quantile(0.25)),
        "p75": float(s.quantile(0.75)),
        "p90": float(s.quantile(0.90)),
        "p95": float(s.quantile(0.95)),
        "max": float(s.max()),
    }


def grouped_means(df: pd.DataFrame, label_col: str, feature_cols: list[str]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for col in feature_cols:
        tmp = df[[label_col, col]].dropna()
        if tmp.empty:
            continue
        out[col] = {
            "normal_mean": float(tmp.loc[~tmp[label_col], col].mean()),
            "future_gap_mean": float(tmp.loc[tmp[label_col], col].mean()),
            "normal_median": float(tmp.loc[~tmp[label_col], col].median()),
            "future_gap_median": float(tmp.loc[tmp[label_col], col].median()),
        }
    return out


def lift_by_top_decile(df: pd.DataFrame, feature: str, label: str, *, high_is_risk: bool = True) -> dict[str, float]:
    tmp = df[[feature, label]].dropna()
    if tmp.empty:
        return {}
    threshold = tmp[feature].quantile(0.90 if high_is_risk else 0.10)
    segment = tmp[feature] >= threshold if high_is_risk else tmp[feature] <= threshold
    baseline = tmp[label].mean()
    segment_rate = tmp.loc[segment, label].mean()
    return {
        "threshold": float(threshold),
        "baseline_future_gap_rate": float(baseline),
        "segment_future_gap_rate": float(segment_rate),
        "lift": float(segment_rate / baseline) if baseline else np.nan,
        "segment_rows": int(segment.sum()),
    }


def main() -> None:
    ensure_dirs()
    orders = pd.read_csv(
        DATA / "orders_clean.csv",
        usecols=[
            "order_id",
            "user_id",
            "eval_set",
            "order_number",
            "order_dow",
            "order_hour_of_day",
            "days_since_prior_order",
            "relative_day",
        ],
    )
    behavior = pd.read_csv(
        DATA / "user_order_behavior_base.csv",
        usecols=[
            "order_id",
            "user_id",
            "eval_set",
            "order_number",
            "order_dow",
            "order_hour_of_day",
            "days_since_prior_order",
            "relative_day",
            "item_count",
            "unique_product_count",
            "reorder_item_count",
            "distinct_aisle_count",
            "distinct_department_count",
            "reorder_ratio",
            "is_last_observed_order",
            "next_days_until_order",
            "has_next_order_observed",
            "prior_avg_gap_days",
            "prior_avg_item_count",
            "prior_avg_reorder_ratio",
            "prior_avg_distinct_department_count",
            "gap_ratio_to_prior_avg",
            "basket_size_ratio_to_prior_avg",
            "reorder_ratio_delta_from_prior_avg",
            "department_count_ratio_to_prior_avg",
            "candidate_future_gap_30d",
            "candidate_future_gap_2x_prior_avg",
        ],
    )
    user_summary = pd.read_csv(DATA / "user_behavior_summary.csv")

    orders_per_user = orders.groupby("user_id")["order_id"].nunique()
    save_hist(
        orders_per_user,
        "Instacart orders per user",
        "Orders per user",
        PLOTS / "orders_per_user_distribution.png",
        bins=60,
        logy=True,
    )
    save_hist(
        user_summary["observed_span_days"],
        "Instacart reconstructed user timeline span",
        "Observed span in relative days",
        PLOTS / "user_span_distribution.png",
        bins=60,
    )
    save_hist(
        behavior["days_since_prior_order"],
        "Instacart days since prior order",
        "Days since prior order",
        PLOTS / "gap_distribution.png",
        bins=31,
    )
    save_hist(
        behavior["item_count"],
        "Instacart basket size distribution",
        "Items per order",
        PLOTS / "basket_size_distribution.png",
        bins=70,
        logy=True,
    )
    save_hist(
        behavior["reorder_ratio"],
        "Instacart reorder ratio distribution",
        "Reorder ratio",
        PLOTS / "reorder_ratio_distribution.png",
        bins=50,
    )
    save_hist(
        behavior["gap_ratio_to_prior_avg"].clip(upper=5),
        "Instacart gap acceleration ratio, clipped at 5x",
        "Current gap / prior average gap",
        PLOTS / "gap_ratio_distribution.png",
        bins=60,
    )

    valid_prediction_rows = behavior[
        behavior["has_next_order_observed"]
        & behavior["prior_avg_gap_days"].notna()
        & behavior["prior_avg_gap_days"].gt(0)
        & behavior["order_number"].ge(3)
    ].copy()

    save_boxplot_by_label(
        valid_prediction_rows,
        "gap_ratio_to_prior_avg",
        "candidate_future_gap_30d",
        "Current gap acceleration vs future 30-day gap",
        "Current gap / prior average gap",
        PLOTS / "gap_ratio_by_future_gap.png",
    )
    save_boxplot_by_label(
        valid_prediction_rows,
        "basket_size_ratio_to_prior_avg",
        "candidate_future_gap_30d",
        "Basket size ratio vs future 30-day gap",
        "Current basket / prior average basket",
        PLOTS / "basket_ratio_by_future_gap.png",
    )
    save_boxplot_by_label(
        valid_prediction_rows,
        "reorder_ratio_delta_from_prior_avg",
        "candidate_future_gap_30d",
        "Reorder routine change vs future 30-day gap",
        "Current reorder ratio minus prior average",
        PLOTS / "reorder_delta_by_future_gap.png",
    )

    dow_counts = behavior["order_dow"].value_counts().sort_index()
    save_bar(dow_counts, "Instacart behavior orders by day of week", "Day of week", "Orders", PLOTS / "orders_by_dow.png")
    hour_counts = behavior["order_hour_of_day"].value_counts().sort_index()
    save_bar(hour_counts, "Instacart behavior orders by hour", "Hour of day", "Orders", PLOTS / "orders_by_hour.png")

    feature_cols = [
        "days_since_prior_order",
        "gap_ratio_to_prior_avg",
        "item_count",
        "basket_size_ratio_to_prior_avg",
        "reorder_ratio",
        "reorder_ratio_delta_from_prior_avg",
        "distinct_department_count",
        "department_count_ratio_to_prior_avg",
    ]
    label_analysis = grouped_means(valid_prediction_rows, "candidate_future_gap_30d", feature_cols)
    lifts = {
        "top_decile_gap_ratio": lift_by_top_decile(valid_prediction_rows, "gap_ratio_to_prior_avg", "candidate_future_gap_30d"),
        "bottom_decile_basket_ratio": lift_by_top_decile(
            valid_prediction_rows, "basket_size_ratio_to_prior_avg", "candidate_future_gap_30d", high_is_risk=False
        ),
        "bottom_decile_reorder_delta": lift_by_top_decile(
            valid_prediction_rows,
            "reorder_ratio_delta_from_prior_avg",
            "candidate_future_gap_30d",
            high_is_risk=False,
        ),
        "bottom_decile_department_ratio": lift_by_top_decile(
            valid_prediction_rows,
            "department_count_ratio_to_prior_avg",
            "candidate_future_gap_30d",
            high_is_risk=False,
        ),
    }

    # Product/department actionability from cleaned basket and catalog files.
    # Department counts are computed from raw order-product rows in chunks so the report can say which routines matter.
    catalog = pd.read_csv(DATA / "product_catalog_clean.csv", usecols=["product_id", "department", "aisle"])
    product_to_department = catalog.set_index("product_id")["department"].to_dict()
    dept_counts: dict[str, int] = {}
    raw_dir = ROOT / "data" / "instacart"
    for file_name in ["order_products__prior.csv", "order_products__train.csv"]:
        for chunk in pd.read_csv(raw_dir / file_name, usecols=["product_id"], chunksize=2_000_000):
            departments = chunk["product_id"].map(product_to_department).fillna("unknown")
            vc = departments.value_counts()
            for dept, count in vc.items():
                dept_counts[str(dept)] = dept_counts.get(str(dept), 0) + int(count)
    top_departments = dict(sorted(dept_counts.items(), key=lambda kv: kv[1], reverse=True)[:15])
    save_bar(
        pd.Series(top_departments).sort_values(),
        "Instacart top departments by order-product rows",
        "Department",
        "Order-product rows",
        PLOTS / "top_departments.png",
        rotate=45,
    )

    summary = {
        "dataset": "instacart",
        "scope": {
            "orders": int(orders.shape[0]),
            "users": int(orders["user_id"].nunique()),
            "behavior_orders_with_baskets": int(behavior.shape[0]),
            "test_orders_without_baskets": int((orders["eval_set"] == "test").sum()),
            "eval_set_counts": orders["eval_set"].value_counts().to_dict(),
        },
        "sequence_depth": {
            "orders_per_user": describe(orders_per_user),
            "observed_span_days": describe(user_summary["observed_span_days"]),
            "users_3plus_orders": int((orders_per_user >= 3).sum()),
            "users_5plus_orders": int((orders_per_user >= 5).sum()),
            "users_10plus_orders": int((orders_per_user >= 10).sum()),
        },
        "behavior_distributions": {
            "days_since_prior_order": describe(behavior["days_since_prior_order"]),
            "item_count": describe(behavior["item_count"]),
            "reorder_ratio": describe(behavior["reorder_ratio"]),
            "distinct_department_count": describe(behavior["distinct_department_count"]),
            "gap_ratio_to_prior_avg": describe(valid_prediction_rows["gap_ratio_to_prior_avg"]),
            "basket_size_ratio_to_prior_avg": describe(valid_prediction_rows["basket_size_ratio_to_prior_avg"]),
            "reorder_ratio_delta_from_prior_avg": describe(valid_prediction_rows["reorder_ratio_delta_from_prior_avg"]),
            "department_count_ratio_to_prior_avg": describe(valid_prediction_rows["department_count_ratio_to_prior_avg"]),
        },
        "label_feasibility": {
            "valid_prediction_rows": int(valid_prediction_rows.shape[0]),
            "future_30d_gap_rows": int(valid_prediction_rows["candidate_future_gap_30d"].sum()),
            "future_30d_gap_rate": float(valid_prediction_rows["candidate_future_gap_30d"].mean()),
            "future_2x_prior_avg_gap_rows": int(valid_prediction_rows["candidate_future_gap_2x_prior_avg"].sum()),
            "future_2x_prior_avg_gap_rate": float(valid_prediction_rows["candidate_future_gap_2x_prior_avg"].mean()),
        },
        "future_gap_feature_comparison": label_analysis,
        "future_gap_lifts": lifts,
        "top_departments": top_departments,
    }

    with (REPORT / "instacart_eda_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    lines = [
        "# Instacart EDA Report",
        "",
        "## Executive Takeaway",
        (
            "Instacart is a strong primary dataset for early behavioral decay modeling. It has repeated "
            "user order sequences, reconstructed relative timelines, basket size, reorder behavior, and "
            "product/category structure."
        ),
        "",
        "## Scope",
        f"- Orders: {summary['scope']['orders']:,}.",
        f"- Users: {summary['scope']['users']:,}.",
        f"- Behavior orders with basket detail: {summary['scope']['behavior_orders_with_baskets']:,}.",
        f"- Test orders without basket detail: {summary['scope']['test_orders_without_baskets']:,}.",
        f"- Eval sets: {summary['scope']['eval_set_counts']}.",
        "",
        "## Sequence Depth",
        f"- Median orders per user: {summary['sequence_depth']['orders_per_user']['median']:.1f}.",
        f"- Median reconstructed span: {summary['sequence_depth']['observed_span_days']['median']:.1f} days.",
        f"- Users with 5+ orders: {summary['sequence_depth']['users_5plus_orders']:,}.",
        f"- Users with 10+ orders: {summary['sequence_depth']['users_10plus_orders']:,}.",
        "",
        "## Behavioral Signal Distributions",
        f"- Median gap between orders: {summary['behavior_distributions']['days_since_prior_order']['median']:.1f} days.",
        f"- Median basket size: {summary['behavior_distributions']['item_count']['median']:.1f} items.",
        f"- Median reorder ratio: {summary['behavior_distributions']['reorder_ratio']['median']:.2f}.",
        f"- Median distinct departments per basket: {summary['behavior_distributions']['distinct_department_count']['median']:.1f}.",
        "",
        "## Future Inactivity Label Feasibility",
        f"- Valid sequence rows for next-gap modeling: {summary['label_feasibility']['valid_prediction_rows']:,}.",
        (
            f"- Rows followed by a future 30-day gap: {summary['label_feasibility']['future_30d_gap_rows']:,} "
            f"({pct(summary['label_feasibility']['future_30d_gap_rate'])})."
        ),
        (
            f"- Rows followed by a future gap at least 2x prior average: "
            f"{summary['label_feasibility']['future_2x_prior_avg_gap_rows']:,} "
            f"({pct(summary['label_feasibility']['future_2x_prior_avg_gap_rate'])})."
        ),
        "",
        "## Early Indicator Readout",
        "| Feature | Normal median | Future 30d gap median |",
        "|---|---:|---:|",
    ]
    for feature, stats in label_analysis.items():
        lines.append(f"| {feature} | {stats['normal_median']:.3f} | {stats['future_gap_median']:.3f} |")

    lines.extend(
        [
            "",
            "## Segment Lift Checks",
            "| Segment | Threshold | Future gap rate | Lift vs baseline | Rows |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for name, stats in lifts.items():
        if not stats:
            continue
        lines.append(
            f"| {name} | {stats['threshold']:.3f} | {pct(stats['segment_future_gap_rate'])} | "
            f"{stats['lift']:.2f}x | {stats['segment_rows']:,} |"
        )

    lines.extend(
        [
            "",
            "## Actionable Intervention Mapping",
            "- High gap acceleration: replenishment reminder or timing-based reactivation.",
            "- Basket size contraction: personalized bundle, minimum-cart incentive, or basket-builder recommendation.",
            "- Reorder ratio decline: one-click reorder of usual products or staple recovery prompt.",
            "- Department/category narrowing: category-specific offer or recommendation to restore routine breadth.",
            "- Routine timing irregularity: habit-restoration reminder keyed to the user's normal reorder interval.",
            "",
            "## Recommended Use",
            "- Use Instacart as the main dataset for the behavioral decay project.",
            "- Build labels around future gap expansion, not generic calendar churn.",
            "- Compare leading decay features against traditional RFM-style baselines using the same model family.",
            "",
            "## Plots",
            "- `plots/orders_per_user_distribution.png`",
            "- `plots/user_span_distribution.png`",
            "- `plots/gap_distribution.png`",
            "- `plots/basket_size_distribution.png`",
            "- `plots/reorder_ratio_distribution.png`",
            "- `plots/gap_ratio_distribution.png`",
            "- `plots/gap_ratio_by_future_gap.png`",
            "- `plots/basket_ratio_by_future_gap.png`",
            "- `plots/reorder_delta_by_future_gap.png`",
            "- `plots/orders_by_dow.png`",
            "- `plots/orders_by_hour.png`",
            "- `plots/top_departments.png`",
        ]
    )
    (REPORT / "instacart_eda.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary["label_feasibility"], indent=2))


if __name__ == "__main__":
    main()
