from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FEATURE_DIR = ROOT / "data" / "processed" / "instacart" / "features"
REPORT = ROOT / "reports" / "features" / "instacart" / "matrix"


KEY_COLS = ["user_id", "order_id"]
NON_PREDICTOR_COLS = {*KEY_COLS, "split", "early_decay_label", "eval_set", "order_number"}
FORBIDDEN_PREDICTOR_COLS = {
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


def validate_unique_keys(df: pd.DataFrame, name: str) -> None:
    duplicate_count = int(df.duplicated(KEY_COLS).sum())
    if duplicate_count:
        raise ValueError(f"{name} has {duplicate_count:,} duplicate user_id/order_id rows")


def main() -> None:
    ensure_dirs()

    leading = pd.read_pickle(FEATURE_DIR / "instacart_leading_features_model_input.pkl")
    baseline = pd.read_pickle(FEATURE_DIR / "instacart_baseline_features_model_input.pkl")
    targets = pd.read_pickle(FEATURE_DIR / "instacart_leading_feature_targets.pkl")

    validate_unique_keys(leading, "leading")
    validate_unique_keys(baseline, "baseline")
    validate_unique_keys(targets, "targets")

    leading_feature_cols = [col for col in leading.columns if col not in NON_PREDICTOR_COLS]
    baseline_feature_cols = [
        col for col in baseline.columns if col not in NON_PREDICTOR_COLS
    ]
    matrix = (
        targets.merge(leading[KEY_COLS + leading_feature_cols], on=KEY_COLS, how="inner", validate="one_to_one")
        .merge(baseline[KEY_COLS + baseline_feature_cols], on=KEY_COLS, how="inner", validate="one_to_one")
    )

    if matrix.shape[0] != targets.shape[0]:
        raise ValueError(
            f"Feature matrix row count {matrix.shape[0]:,} does not match target rows {targets.shape[0]:,}"
        )

    predictor_cols = [
        col
        for col in matrix.columns
        if col not in NON_PREDICTOR_COLS
    ]
    leaked_cols = sorted(FORBIDDEN_PREDICTOR_COLS & set(predictor_cols))
    if leaked_cols:
        raise ValueError(f"Forbidden predictor columns present: {leaked_cols}")

    matrix.to_pickle(FEATURE_DIR / "instacart_feature_matrix.pkl")
    matrix.sample(min(len(matrix), 100_000), random_state=42).to_csv(
        FEATURE_DIR / "instacart_feature_matrix_sample.csv",
        index=False,
    )

    split_summary = (
        matrix.groupby("split")["early_decay_label"]
        .agg(rows="count", positive_rows="sum", positive_rate="mean")
        .reset_index()
    )
    source_counts = {
        "leading_rows": int(leading.shape[0]),
        "baseline_rows": int(baseline.shape[0]),
        "target_rows": int(targets.shape[0]),
        "feature_matrix_rows": int(matrix.shape[0]),
        "predictor_columns": int(len(predictor_cols)),
        "leading_predictor_columns": int(
            len(leading_feature_cols)
        ),
        "baseline_predictor_columns": int(len(baseline_feature_cols)),
    }
    report = {
        "source_counts": source_counts,
        "quality_checks": {
            "duplicate_user_order_rows": int(matrix.duplicated(KEY_COLS).sum()),
            "forbidden_predictor_columns": leaked_cols,
            "null_rates_top_15": {
                key: float(value)
                for key, value in matrix[predictor_cols].isna().mean().sort_values(ascending=False).head(15).to_dict().items()
            },
        },
        "split_summary": split_summary.to_dict(orient="records"),
        "outputs": {
            "feature_matrix_pickle": str(FEATURE_DIR / "instacart_feature_matrix.pkl"),
            "feature_matrix_sample_csv": str(FEATURE_DIR / "instacart_feature_matrix_sample.csv"),
            "report_json": str(REPORT / "instacart_feature_matrix_report.json"),
            "report_md": str(REPORT / "instacart_feature_matrix_report.md"),
        },
    }

    with (REPORT / "instacart_feature_matrix_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    lines = [
        "# Instacart Feature Matrix Validation",
        "",
        "## Scope",
        "",
        "Joined corrected leading features, corrected peer baseline features, and the Phase 2 target into one modeling-ready table.",
        "",
        "## Outputs",
        "",
        f"- Feature matrix: `{report['outputs']['feature_matrix_pickle']}`",
        f"- CSV inspection sample: `{report['outputs']['feature_matrix_sample_csv']}`",
        "",
        "## Source Counts",
        "",
        f"- Leading feature rows: {source_counts['leading_rows']:,}",
        f"- Baseline feature rows: {source_counts['baseline_rows']:,}",
        f"- Target rows: {source_counts['target_rows']:,}",
        f"- Final feature matrix rows: {source_counts['feature_matrix_rows']:,}",
        f"- Predictor columns: {source_counts['predictor_columns']:,}",
        f"- Leading predictor columns: {source_counts['leading_predictor_columns']:,}",
        f"- Baseline predictor columns: {source_counts['baseline_predictor_columns']:,}",
        "",
        "## Split Summary",
        "",
        "| Split | Rows | Positive Rows | Positive Rate |",
        "|---|---:|---:|---:|",
    ]
    for row in split_summary.to_dict(orient="records"):
        lines.append(
            f"| {row['split']} | {int(row['rows']):,} | {int(row['positive_rows']):,} | {float(row['positive_rate']):.2%} |"
        )
    lines.extend(
        [
            "",
            "## Quality Checks",
            "",
            f"- Duplicate `user_id, order_id` rows: {report['quality_checks']['duplicate_user_order_rows']:,}",
            f"- Forbidden predictor columns: {report['quality_checks']['forbidden_predictor_columns']}",
            "",
            "## Modeling Notes",
            "",
            "- Use `early_decay_label` as the target.",
            "- Use `split` for train/validation/test separation.",
            "- Treat `user_id` and `order_id` as keys only, not predictors.",
            "- Encode `base_order_dow` and `base_order_hour` before linear models.",
        ]
    )
    (REPORT / "instacart_feature_matrix_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(source_counts, indent=2))


if __name__ == "__main__":
    main()
