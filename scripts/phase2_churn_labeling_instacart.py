from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed" / "instacart"
OUT = PROCESSED / "labels"
REPORT = ROOT / "reports" / "phase2"


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)


def pct(value: float) -> str:
    return f"{value:.2%}"


def describe_bool(series: pd.Series) -> dict[str, int | float]:
    clean = series.dropna().astype(bool)
    return {
        "rows": int(clean.shape[0]),
        "positive_rows": int(clean.sum()),
        "positive_rate": float(clean.mean()) if clean.shape[0] else 0.0,
    }


def add_full_next_gap(orders: pd.DataFrame) -> pd.DataFrame:
    orders = orders.sort_values(["user_id", "order_number"]).copy()
    orders["next_order_id"] = orders.groupby("user_id")["order_id"].shift(-1)
    orders["next_order_number"] = orders.groupby("user_id")["order_number"].shift(-1)
    orders["next_eval_set"] = orders.groupby("user_id")["eval_set"].shift(-1)
    orders["next_gap_days"] = orders.groupby("user_id")["days_since_prior_order"].shift(-1)
    orders["has_observed_next_order"] = orders["next_gap_days"].notna()
    return orders[
        [
            "order_id",
            "next_order_id",
            "next_order_number",
            "next_eval_set",
            "next_gap_days",
            "has_observed_next_order",
        ]
    ]


def add_historical_gap_median(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["user_id", "order_number"]).copy()
    known_gap = df["days_since_prior_order"].notna()
    df["known_gap_count_to_date"] = known_gap.astype("int32").groupby(df["user_id"]).cumsum()
    df["historical_median_gap_days"] = (
        df.groupby("user_id")["days_since_prior_order"]
        .expanding(min_periods=1)
        .median()
        .reset_index(level=0, drop=True)
    )
    return df


def deterministic_user_split(user_id: int) -> str:
    bucket = (int(user_id) * 2654435761) % 100
    if bucket < 70:
        return "train"
    if bucket < 85:
        return "validation"
    return "test"


def sensitivity_table(snapshots: pd.DataFrame) -> list[dict[str, int | float]]:
    rows: list[dict[str, int | float]] = []
    for min_known_gaps in [2, 3, 5, 9]:
        base = snapshots[
            snapshots["has_observed_next_order"]
            & snapshots["historical_median_gap_days"].gt(0)
            & (snapshots["known_gap_count_to_date"] >= min_known_gaps)
        ]
        rows.append(
            {
                "rule": "next_gap_eq_30",
                "min_known_gaps": min_known_gaps,
                "eligible_rows": int(base.shape[0]),
                "positive_rows": int(base["next_gap_30d_label"].sum()),
                "positive_rate": float(base["next_gap_30d_label"].mean()) if base.shape[0] else 0.0,
                "censored_uncertain_rows_excluded": 0,
                "eligible_users": int(base["user_id"].nunique()),
            }
        )
        for multiplier in [1.5, 2.0, 2.5]:
            censored_uncertain = base["next_gap_days"].eq(30) & (
                30 < multiplier * base["historical_median_gap_days"]
            )
            eval_base = base[~censored_uncertain]
            label = eval_base["next_gap_days"] >= multiplier * eval_base["historical_median_gap_days"]
            rows.append(
                {
                    "rule": f"next_gap_ge_{multiplier}x_historical_median",
                    "min_known_gaps": min_known_gaps,
                    "eligible_rows": int(eval_base.shape[0]),
                    "positive_rows": int(label.sum()),
                    "positive_rate": float(label.mean()) if eval_base.shape[0] else 0.0,
                    "censored_uncertain_rows_excluded": int(censored_uncertain.sum()),
                    "eligible_users": int(eval_base["user_id"].nunique()),
                }
            )
        hybrid = base["next_gap_30d_label"] | (
            base["next_gap_days"] >= 2.0 * base["historical_median_gap_days"]
        )
        rows.append(
            {
                "rule": "hybrid_next_gap_30_or_2x_median",
                "min_known_gaps": min_known_gaps,
                "eligible_rows": int(base.shape[0]),
                "positive_rows": int(hybrid.sum()),
                "positive_rate": float(hybrid.mean()) if base.shape[0] else 0.0,
                "censored_uncertain_rows_excluded": 0,
                "eligible_users": int(base["user_id"].nunique()),
            }
        )
    return rows


def main() -> None:
    ensure_dirs()

    behavior = pd.read_csv(PROCESSED / "user_order_behavior_base.csv")
    orders = pd.read_csv(
        PROCESSED / "orders_clean.csv",
        usecols=["order_id", "user_id", "eval_set", "order_number", "days_since_prior_order", "relative_day"],
    )

    full_next_gap = add_full_next_gap(orders)
    snapshots = behavior.merge(full_next_gap, on="order_id", how="left", validate="one_to_one")
    snapshots = add_historical_gap_median(snapshots)

    snapshots["next_gap_30d_label"] = snapshots["next_gap_days"].eq(30)
    snapshots["next_gap_2x_median_label"] = (
        snapshots["historical_median_gap_days"].gt(0)
        & snapshots["next_gap_days"].notna()
        & (snapshots["next_gap_days"] >= 2.0 * snapshots["historical_median_gap_days"])
    )
    snapshots["next_gap_1_5x_median_label"] = (
        snapshots["historical_median_gap_days"].gt(0)
        & snapshots["next_gap_days"].notna()
        & (snapshots["next_gap_days"] >= 1.5 * snapshots["historical_median_gap_days"])
    )
    snapshots["next_gap_2_5x_median_label"] = (
        snapshots["historical_median_gap_days"].gt(0)
        & snapshots["next_gap_days"].notna()
        & (snapshots["next_gap_days"] >= 2.5 * snapshots["historical_median_gap_days"])
    )

    # Final Phase 2 label. We require three known gaps up to the current snapshot, including the current
    # order's observed prior gap, so the user's normal rhythm is not based on one or two gaps.
    # That means the current snapshot usually starts at order_number 4+.
    #
    # The 30-day cap is not an automatic label. Instacart caps long gaps at 30, so it is a
    # censored severity signal used for ranking, not proof of churn by itself.
    base_label_eligible = (
        snapshots["has_observed_next_order"]
        & snapshots["historical_median_gap_days"].gt(0)
        & snapshots["known_gap_count_to_date"].ge(3)
    )
    snapshots["censored_uncertain_label"] = (
        base_label_eligible
        & snapshots["next_gap_days"].eq(30)
        & (30 < 2.0 * snapshots["historical_median_gap_days"])
        & ~snapshots["next_gap_2x_median_label"]
    )
    snapshots["label_eligible"] = base_label_eligible & ~snapshots["censored_uncertain_label"]
    snapshots["early_decay_label"] = snapshots["label_eligible"] & snapshots["next_gap_2x_median_label"]
    snapshots["gap_cap_30_flag"] = snapshots["label_eligible"] & snapshots["next_gap_30d_label"]
    snapshots["next_gap_ratio_to_historical_median"] = (
        snapshots["next_gap_days"] / snapshots["historical_median_gap_days"]
    ).replace([np.inf, -np.inf], np.nan)

    reliability = np.select(
        [
            snapshots["known_gap_count_to_date"].ge(9),
            snapshots["known_gap_count_to_date"].ge(5),
            snapshots["known_gap_count_to_date"].ge(3),
        ],
        [1.0, 0.85, 0.70],
        default=0.0,
    )
    cap_boost = np.where(snapshots["gap_cap_30_flag"], 0.50, 0.0)
    snapshots["decay_severity_score"] = np.where(
        snapshots["label_eligible"],
        snapshots["next_gap_ratio_to_historical_median"].clip(lower=0, upper=5) * reliability + cap_boost,
        np.nan,
    )
    snapshots["decay_severity_tier"] = np.select(
        [
            snapshots["censored_uncertain_label"],
            ~snapshots["label_eligible"],
            snapshots["early_decay_label"] & snapshots["gap_cap_30_flag"] & snapshots["historical_median_gap_days"].le(10),
            snapshots["early_decay_label"] & snapshots["gap_cap_30_flag"],
            snapshots["early_decay_label"],
            snapshots["next_gap_1_5x_median_label"] | snapshots["gap_cap_30_flag"],
        ],
        [
            "censored_uncertain",
            "not_eligible",
            "critical_capped_gap_fast_cadence",
            "high_capped_gap",
            "valid_decay_warning",
            "watchlist",
        ],
        default="normal",
    )

    snapshots["label_definition"] = np.where(
        snapshots["label_eligible"],
        "next_gap_ge_2x_historical_median_after_3_known_gaps",
        "not_label_eligible",
    )
    snapshots["label_status"] = np.select(
        [
            snapshots["label_eligible"],
            snapshots["censored_uncertain_label"],
        ],
        [
            "labeled",
            "censored_uncertain",
        ],
        default="not_label_eligible",
    )
    snapshots["split"] = snapshots["user_id"].map(deterministic_user_split)

    label_cols = [
        "user_id",
        "order_id",
        "eval_set",
        "order_number",
        "relative_day",
        "item_count",
        "unique_product_count",
        "reorder_item_count",
        "distinct_aisle_count",
        "distinct_department_count",
        "reorder_ratio",
        "days_since_prior_order",
        "known_gap_count_to_date",
        "historical_median_gap_days",
        "gap_ratio_to_prior_avg",
        "basket_size_ratio_to_prior_avg",
        "reorder_ratio_delta_from_prior_avg",
        "department_count_ratio_to_prior_avg",
        "next_order_id",
        "next_order_number",
        "next_eval_set",
        "next_gap_days",
        "next_gap_ratio_to_historical_median",
        "has_observed_next_order",
        "label_eligible",
        "censored_uncertain_label",
        "next_gap_30d_label",
        "gap_cap_30_flag",
        "next_gap_1_5x_median_label",
        "next_gap_2x_median_label",
        "next_gap_2_5x_median_label",
        "early_decay_label",
        "decay_severity_score",
        "decay_severity_tier",
        "label_definition",
        "label_status",
        "split",
    ]
    label_table = snapshots[label_cols].copy()
    label_table.to_csv(OUT / "instacart_phase2_decay_labels.csv", index=False)

    eligible = label_table[label_table["label_eligible"]].copy()
    split_summary = (
        eligible.groupby("split")["early_decay_label"]
        .agg(rows="count", positive_rows="sum", positive_rate="mean")
        .reset_index()
    )
    sensitivity = sensitivity_table(snapshots)

    report = {
        "final_label": {
            "name": "early_decay_label",
            "definition": "eligible snapshot where next_gap_days >= 2x historical_median_gap_days",
            "eligibility": "current snapshot has observed next order, historical_median_gap_days > 0, at least 3 known gaps up to the current order, and is not censored-uncertain",
            "severity_method": "next_gap_days == 30 is used as a capped-gap severity/ranking signal, not as an automatic positive label",
            "why_not_90_day_churn": "Instacart has relative timelines and days_since_prior_order is capped at 30, so 60/90/120 calendar-day churn windows are not valid labels.",
        },
        "counts": {
            "snapshot_rows_with_current_basket": int(label_table.shape[0]),
            "label_eligible_rows": int(eligible.shape[0]),
            "label_eligible_users": int(eligible["user_id"].nunique()),
            "early_decay_positive_rows": int(eligible["early_decay_label"].sum()),
            "early_decay_positive_rate": float(eligible["early_decay_label"].mean()),
            "censored_uncertain_rows_excluded": int(label_table["censored_uncertain_label"].sum()),
            "censored_uncertain_users_excluded": int(
                label_table.loc[label_table["censored_uncertain_label"], "user_id"].nunique()
            ),
            "next_gap_30d": describe_bool(eligible["next_gap_30d_label"]),
            "next_gap_2x_median": describe_bool(eligible["next_gap_2x_median_label"]),
        },
        "severity_tier_counts": (
            eligible["decay_severity_tier"]
            .value_counts()
            .rename_axis("tier")
            .reset_index(name="rows")
            .to_dict(orient="records")
        ),
        "split_summary": split_summary.to_dict(orient="records"),
        "sensitivity": sensitivity,
        "leakage_controls": {
            "unit_of_prediction": "user-order snapshot after current order",
            "target_source": "next order gap from orders_clean.csv",
            "feature_timing": "current and historical behavior only; next_* columns should be excluded from model features",
            "user_split": "deterministic user_id hash split so the same user does not appear in multiple modeling splits",
        },
        "outputs": {
            "labels_csv": (OUT / "instacart_phase2_decay_labels.csv").relative_to(ROOT).as_posix(),
            "report_json": (REPORT / "instacart_phase2_label_report.json").relative_to(ROOT).as_posix(),
            "report_md": (REPORT / "instacart_phase2_label_definition.md").relative_to(ROOT).as_posix(),
        },
    }

    with (REPORT / "instacart_phase2_label_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    lines = [
        "# Phase 2 Churn Label Definition - Instacart",
        "",
        "## Decision",
        "",
        "Use a **future purchase-rhythm decay** label, not a generic 90-day churn label.",
        "",
        "Final label: `early_decay_label = 1` when an eligible user-order snapshot is followed by:",
        "",
        "- `next_gap_days >= 2x historical_median_gap_days`, because the next purchase is materially slower than the user's own normal rhythm.",
        "",
        "`next_gap_days == 30` is not treated as an automatic positive label. It is used as a severity/ranking signal because Instacart caps long gaps at 30 days. The true gap may be 30 days or longer, but the cap alone does not prove churn.",
        "",
        "Eligibility:",
        "",
        "- The current order has basket behavior available.",
        "- The next order gap is observed.",
        "- The user's historical median gap is greater than 0.",
        "- The snapshot has at least 3 known gaps up to the current order, including the current order's observed prior gap.",
        "- The row is not censored-uncertain. If `next_gap_days == 30` but the user's 2x threshold is above 30 days, the true label cannot be observed because Instacart caps gaps at 30.",
        "",
        "## Why Not 60/90/120-Day Churn",
        "",
        "That would be the wrong label for Instacart. The dataset does not provide real calendar dates, and `days_since_prior_order` is capped at 30. A 90-day no-purchase label would sound professional but would not be measurable from this data.",
        "",
        "## Final Label Counts",
        "",
        f"- Snapshot rows with current basket behavior: {report['counts']['snapshot_rows_with_current_basket']:,}.",
        f"- Label-eligible rows: {report['counts']['label_eligible_rows']:,}.",
        f"- Label-eligible users: {report['counts']['label_eligible_users']:,}.",
        f"- Early-decay positive rows: {report['counts']['early_decay_positive_rows']:,}.",
        f"- Early-decay positive rate: {pct(report['counts']['early_decay_positive_rate'])}.",
        f"- Censored-uncertain rows excluded from supervised labeling: {report['counts']['censored_uncertain_rows_excluded']:,}.",
        f"- Censored-uncertain users excluded from supervised labeling: {report['counts']['censored_uncertain_users_excluded']:,}.",
        f"- Rows hitting the 30-day cap: {report['counts']['next_gap_30d']['positive_rows']:,} ({pct(report['counts']['next_gap_30d']['positive_rate'])}).",
        "",
        "## Severity Tiers",
        "",
        "| Tier | Rows |",
        "|---|---:|",
    ]
    for row in report["severity_tier_counts"]:
        lines.append(f"| {row['tier']} | {row['rows']:,} |")

    lines.extend(
        [
            "",
            "Severity logic:",
            "",
            "- `valid_decay_warning`: next gap is at least 2x the user's historical median.",
            "- `high_capped_gap`: positive label and the observed next gap hits the 30-day cap.",
            "- `critical_capped_gap_fast_cadence`: high capped gap where the user's normal median gap is 10 days or less.",
            "- `watchlist`: not a final positive label, but shows a softer warning such as 1.5x slowdown or a capped 30-day gap.",
            "- `censored_uncertain`: capped 30-day gap where the user's 2x threshold is above the observable range; excluded from supervised labels.",
            "- `normal`: eligible row without a material future slowdown.",
            "",
        ]
    )

    lines.extend(
        [
            "",
            "## Modeling Split",
            "",
            "The label table includes a deterministic user-level split. This avoids putting the same user into train and test, which would inflate performance.",
            "",
            "| Split | Rows | Positive rows | Positive rate |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in split_summary.to_dict(orient="records"):
        lines.append(
            f"| {row['split']} | {int(row['rows']):,} | {int(row['positive_rows']):,} | {pct(float(row['positive_rate']))} |"
        )

    lines.extend(
        [
            "",
            "## Sensitivity Analysis",
            "",
            "| Rule | Min known gaps | Eligible rows | Positive rows | Positive rate | Censored uncertain rows excluded | Eligible users |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in sensitivity:
        lines.append(
            f"| {row['rule']} | {row['min_known_gaps']} | {row['eligible_rows']:,} | "
            f"{row['positive_rows']:,} | {pct(row['positive_rate'])} | "
            f"{row['censored_uncertain_rows_excluded']:,} | {row['eligible_users']:,} |"
        )

    lines.extend(
        [
            "",
            "## Leakage Rules For Phase 4",
            "",
            "- Use `early_decay_label` as the target.",
            "- Use `decay_severity_score`, `decay_severity_tier`, and `gap_cap_30_flag` for ranking/intervention analysis, not as direct model features unless you are intentionally building a post-model prioritization layer.",
            "- Use only rows where `label_eligible == True`.",
            "- Keep `label_status == 'censored_uncertain'` rows out of supervised training and final test metrics.",
            "- Do not use `next_order_id`, `next_order_number`, `next_eval_set`, `next_gap_days`, or any label columns as features.",
            "- Do not use `user_id` as a model feature.",
            "- Use the provided `split` column unless you intentionally run a separate time-style experiment.",
            "",
            "## Output",
            "",
            "- `data/processed/instacart/labels/instacart_phase2_decay_labels.csv`",
        ]
    )
    (REPORT / "instacart_phase2_label_definition.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(report["counts"], indent=2))


if __name__ == "__main__":
    main()
