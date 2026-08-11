from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.features_baseline import build_baseline_features  # noqa: E402


PROCESSED = ROOT / "data" / "processed" / "instacart"
FEATURE_DIR = PROCESSED / "features"
LABELS = PROCESSED / "labels" / "instacart_phase2_decay_labels.csv"
REPORT = ROOT / "reports" / "features" / "instacart" / "baseline"


FEATURE_INPUT_COLS = [
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
]

FORBIDDEN_FEATURE_COLS = {
    "early_decay_label",
    "label_eligible",
    "label_status",
    "next_order_id",
    "next_order_number",
    "next_eval_set",
    "next_gap_days",
    "next_gap_ratio_to_historical_median",
    "next_gap_30d_label",
    "gap_cap_30_flag",
    "next_gap_1_5x_median_label",
    "next_gap_2x_median_label",
    "next_gap_2_5x_median_label",
    "decay_severity_score",
    "decay_severity_tier",
    "label_definition",
}


def ensure_dirs() -> None:
    FEATURE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)


def auc_score(values: pd.Series, labels: pd.Series, *, high_is_risk: bool) -> float:
    tmp = pd.DataFrame({"value": values, "label": labels}).dropna()
    if tmp["label"].nunique() < 2:
        return float("nan")
    ranks = tmp["value"].rank(method="average")
    pos = tmp["label"].astype(bool)
    n_pos = int(pos.sum())
    n_neg = int((~pos).sum())
    auc_high = (float(ranks[pos].sum()) - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
    return float(auc_high if high_is_risk else 1 - auc_high)


def summarize_feature(df: pd.DataFrame, feature: str) -> dict[str, float | int | str]:
    tmp = df[[feature, "early_decay_label"]].dropna()
    auc_high = auc_score(tmp[feature], tmp["early_decay_label"], high_is_risk=True)
    direction = "high" if auc_high >= 0.5 else "low"
    auc = auc_high if direction == "high" else 1 - auc_high
    threshold = tmp[feature].quantile(0.90 if direction == "high" else 0.10)
    segment = tmp[feature].ge(threshold) if direction == "high" else tmp[feature].le(threshold)
    baseline = float(tmp["early_decay_label"].mean())
    segment_rate = float(tmp.loc[segment, "early_decay_label"].mean())
    return {
        "feature": feature,
        "risk_direction": direction,
        "rows": int(tmp.shape[0]),
        "risk_decile_threshold": float(threshold),
        "baseline_decay_rate": baseline,
        "risk_decile_decay_rate": segment_rate,
        "risk_decile_lift": float(segment_rate / baseline) if baseline else float("nan"),
        "univariate_auc_directional": auc,
    }


def pct(value: float) -> str:
    return f"{value:.2%}"


def main() -> None:
    ensure_dirs()

    behavior = pd.read_csv(PROCESSED / "user_order_behavior_base.csv", usecols=FEATURE_INPUT_COLS)
    labels = pd.read_csv(
        LABELS,
        usecols=["user_id", "order_id", "label_eligible", "label_status", "early_decay_label", "split"],
    )
    targets = labels.loc[
        labels["label_eligible"].astype(bool),
        ["user_id", "order_id", "split", "early_decay_label"],
    ].copy()
    targets["early_decay_label"] = targets["early_decay_label"].astype(bool)

    baseline_all = build_baseline_features(behavior)
    baseline = baseline_all.merge(
        targets[["user_id", "order_id"]],
        on=["user_id", "order_id"],
        how="inner",
        validate="one_to_one",
    )
    leaked_cols = sorted(FORBIDDEN_FEATURE_COLS & set(baseline.columns))
    if leaked_cols:
        raise ValueError(f"Forbidden columns present in baseline features: {leaked_cols}")
    if baseline.duplicated(["user_id", "order_id"]).any():
        raise ValueError("Duplicate user_id/order_id rows found in baseline features")

    feature_cols = [c for c in baseline.columns if c not in {"user_id", "order_id", "eval_set", "order_number"}]
    baseline_model = baseline[["user_id", "order_id", *feature_cols]].copy()

    baseline_model.to_pickle(FEATURE_DIR / "instacart_baseline_features_model_input.pkl")
    baseline_model.sample(min(len(baseline_model), 100_000), random_state=42).to_csv(
        FEATURE_DIR / "instacart_baseline_features_model_input_sample.csv",
        index=False,
    )

    validation = baseline_model.merge(targets, on=["user_id", "order_id"], how="inner", validate="one_to_one")
    summaries = sorted(
        [summarize_feature(validation, col) for col in feature_cols],
        key=lambda row: row["univariate_auc_directional"],
        reverse=True,
    )

    report = {
        "inputs": {
            "behavior_rows": int(behavior.shape[0]),
            "current_label_eligible_rows": int(targets.shape[0]),
            "baseline_feature_rows": int(baseline_model.shape[0]),
        },
        "quality_checks": {
            "duplicate_user_order_rows": int(baseline.duplicated(["user_id", "order_id"]).sum()),
            "forbidden_feature_columns": leaked_cols,
            "feature_columns": feature_cols,
        },
        "outputs": {
            "features_pickle": (FEATURE_DIR / "instacart_baseline_features_model_input.pkl").relative_to(ROOT).as_posix(),
            "features_sample_csv": (FEATURE_DIR / "instacart_baseline_features_model_input_sample.csv").relative_to(ROOT).as_posix(),
            "report_json": (REPORT / "instacart_baseline_features_report.json").relative_to(ROOT).as_posix(),
            "report_md": (REPORT / "instacart_baseline_features_report.md").relative_to(ROOT).as_posix(),
        },
        "feature_summaries": summaries,
    }
    with (REPORT / "instacart_baseline_features_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    lines = [
        "# Instacart Baseline Feature Validation",
        "",
        "## Scope",
        "",
        "Built corrected peer baseline features against the current Phase 2 label contract. Censored-uncertain rows are excluded.",
        "",
        "## Outputs",
        "",
        f"- Model-input feature table: `{report['outputs']['features_pickle']}`",
        f"- Feature CSV inspection sample: `{report['outputs']['features_sample_csv']}`",
        "",
        "## Row Counts",
        "",
        f"- Behavior rows processed: {report['inputs']['behavior_rows']:,}",
        f"- Current label-eligible rows: {report['inputs']['current_label_eligible_rows']:,}",
        f"- Baseline feature rows: {report['inputs']['baseline_feature_rows']:,}",
        "",
        "## Feature Separation Summary",
        "",
        "| Feature | Risk Direction | Risk-Decile Decay Rate | Lift | AUC |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['feature']} | {row['risk_direction']} | "
            f"{pct(float(row['risk_decile_decay_rate']))} | "
            f"{float(row['risk_decile_lift']):.2f} | "
            f"{float(row['univariate_auc_directional']):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `base_order_number` was removed because it duplicates `base_total_orders_to_date` in this snapshot design.",
            "- `base_order_dow` and `base_order_hour` should be encoded as categorical or cyclical features for linear models.",
            "- The feature file does not include target or label-status columns.",
        ]
    )
    (REPORT / "instacart_baseline_features_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"baseline_rows": int(baseline_model.shape[0]), "feature_columns": len(feature_cols)}, indent=2))


if __name__ == "__main__":
    main()
