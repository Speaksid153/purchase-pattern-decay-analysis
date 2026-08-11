from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


ROOT = Path(__file__).resolve().parents[1]
FEATURE_MATRIX = ROOT / "data" / "processed" / "instacart" / "features" / "instacart_feature_matrix.pkl"
PREDICTIONS_DIR = ROOT / "data" / "processed" / "instacart" / "predictions"
MODEL_DIR = ROOT / "models" / "phase4"
REPORT_DIR = ROOT / "reports" / "modeling" / "instacart"

KEY_COLS = ["user_id", "order_id"]
TARGET_COL = "early_decay_label"
SPLIT_COL = "split"


def ensure_dirs() -> None:
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def get_feature_groups(df: pd.DataFrame) -> dict[str, list[str]]:
    non_predictors = {*KEY_COLS, TARGET_COL, SPLIT_COL}
    baseline = [col for col in df.columns if col.startswith("base_")]
    leading = [col for col in df.columns if col not in non_predictors and not col.startswith("base_")]
    return {
        "baseline": baseline,
        "leading": leading,
        "combined": leading + baseline,
    }


def validate_matrix(df: pd.DataFrame, feature_groups: dict[str, list[str]]) -> None:
    required = {*KEY_COLS, TARGET_COL, SPLIT_COL}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Feature matrix missing required columns: {missing}")

    duplicate_keys = int(df.duplicated(KEY_COLS).sum())
    if duplicate_keys:
        raise ValueError(f"Feature matrix has {duplicate_keys:,} duplicate user_id/order_id rows")

    expected_splits = {"train", "validation", "test"}
    observed_splits = set(df[SPLIT_COL].dropna().unique())
    if observed_splits != expected_splits:
        raise ValueError(f"Unexpected split values: {sorted(observed_splits)}")

    overlap = sorted(set(feature_groups["baseline"]) & set(feature_groups["leading"]))
    if overlap:
        raise ValueError(f"Baseline/leading feature overlap found: {overlap}")

    if not feature_groups["baseline"] or not feature_groups["leading"]:
        raise ValueError("Both baseline and leading feature groups must be non-empty")


def top_lift(y_true: pd.Series, scores: np.ndarray, fraction: float) -> dict[str, float | int]:
    result = pd.DataFrame({"y_true": y_true.astype(int).to_numpy(), "score": scores})
    result = result.sort_values("score", ascending=False)
    n = max(1, int(len(result) * fraction))
    top_rate = float(result.head(n)["y_true"].mean())
    base_rate = float(result["y_true"].mean())
    return {
        "fraction": fraction,
        "rows": n,
        "positive_rate": top_rate,
        "lift": float(top_rate / base_rate) if base_rate else float("nan"),
    }


def evaluate_predictions(y_true: pd.Series, scores: np.ndarray) -> dict[str, object]:
    predictions = scores >= 0.5
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        predictions,
        average="binary",
        zero_division=0,
    )
    return {
        "roc_auc": float(roc_auc_score(y_true, scores)),
        "pr_auc": float(average_precision_score(y_true, scores)),
        "threshold_0_5": {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "classification_report": classification_report(y_true, predictions, zero_division=0),
        },
        "top_5_pct": top_lift(y_true, scores, 0.05),
        "top_10_pct": top_lift(y_true, scores, 0.10),
    }


def fit_logistic(X_train: pd.DataFrame, y_train: pd.Series) -> Pipeline:
    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    max_iter=500,
                    class_weight="balanced",
                    solver="saga",
                    random_state=42,
                ),
            ),
        ]
    )
    model.fit(X_train, y_train)
    return model


def fit_xgboost(X_train: pd.DataFrame, y_train: pd.Series) -> XGBClassifier:
    scale_pos_weight = float((y_train == 0).sum() / max((y_train == 1).sum(), 1))
    model = XGBClassifier(
        n_estimators=250,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    return model


def predict_scores(model: object, X: pd.DataFrame) -> np.ndarray:
    return np.asarray(model.predict_proba(X)[:, 1])


def save_predictions(
    frame: pd.DataFrame,
    scores_by_model: dict[str, np.ndarray],
    output_path: Path,
) -> None:
    output = frame[[*KEY_COLS, SPLIT_COL, TARGET_COL]].copy()
    for name, scores in scores_by_model.items():
        output[f"risk_score_{name}"] = scores
    output.to_csv(output_path, index=False)


def format_pct(value: float) -> str:
    return f"{value:.2%}"


def metric_rows(results: dict[str, dict[str, dict[str, object]]], split: str) -> Iterable[str]:
    for feature_set, model_results in results.items():
        for model_name, split_results in model_results.items():
            metrics = split_results[split]
            yield (
                f"| {feature_set} | {model_name} | "
                f"{metrics['roc_auc']:.4f} | {metrics['pr_auc']:.4f} | "
                f"{metrics['top_5_pct']['lift']:.2f}x | {metrics['top_10_pct']['lift']:.2f}x | "
                f"{format_pct(metrics['threshold_0_5']['precision'])} | "
                f"{format_pct(metrics['threshold_0_5']['recall'])} |"
            )


def write_report(
    results: dict[str, dict[str, dict[str, object]]],
    feature_groups: dict[str, list[str]],
    split_summary: pd.DataFrame,
    outputs: dict[str, str],
) -> None:
    report = {
        "feature_counts": {key: len(value) for key, value in feature_groups.items()},
        "split_summary": split_summary.to_dict(orient="records"),
        "results": results,
        "outputs": outputs,
        "sync_note": (
            "Phase 4 uses the final combined feature matrix as the sole modeling input. "
            "It does not merge stale baseline CSVs with labels."
        ),
    }
    with (REPORT_DIR / "phase4_modeling_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    best_validation = max(
        (
            (feature_set, model_name, values["validation"]["pr_auc"], values["validation"]["top_5_pct"]["lift"])
            for feature_set, model_values in results.items()
            for model_name, values in model_values.items()
        ),
        key=lambda row: (row[2], row[3]),
    )

    lines = [
        "# Instacart Phase 4 Modeling Report",
        "",
        "## Scope",
        "",
        "Synced Phase 4 modeling against the corrected final feature matrix. This fixes the peer Phase 4 mismatch where an older baseline CSV was merged with labels and produced extra validation rows.",
        "",
        "## Modeling Input",
        "",
        f"- Final matrix rows: {int(split_summary['rows'].sum()):,}",
        f"- Baseline predictors: {len(feature_groups['baseline']):,}",
        f"- Leading predictors: {len(feature_groups['leading']):,}",
        f"- Combined predictors: {len(feature_groups['combined']):,}",
        "",
        "## Split Summary",
        "",
        "| Split | Rows | Positives | Positive Rate |",
        "|---|---:|---:|---:|",
    ]
    for row in split_summary.to_dict(orient="records"):
        lines.append(
            f"| {row['split']} | {int(row['rows']):,} | {int(row['positives']):,} | {format_pct(float(row['positive_rate']))} |"
        )

    lines.extend(
        [
            "",
            "## Validation Metrics",
            "",
            "| Feature Set | Model | ROC-AUC | PR-AUC | Top 5% Lift | Top 10% Lift | Precision @ 0.5 | Recall @ 0.5 |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
            *metric_rows(results, "validation"),
            "",
            "## Test Metrics",
            "",
            "| Feature Set | Model | ROC-AUC | PR-AUC | Top 5% Lift | Top 10% Lift | Precision @ 0.5 | Recall @ 0.5 |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
            *metric_rows(results, "test"),
            "",
            "## Best Validation Result",
            "",
            f"- Best by PR-AUC: `{best_validation[0]}` + `{best_validation[1]}`",
            f"- Validation PR-AUC: {best_validation[2]:.4f}",
            f"- Validation top-5% lift: {best_validation[3]:.2f}x",
            "",
            "## Practical Read",
            "",
            "- Use PR-AUC and top-decile lift as the main comparison metrics because this is an intervention-ranking problem, not a pure 0.5-threshold classifier.",
            "- The baseline-only model is the traditional comparison point.",
            "- The leading-only model tests the project thesis directly.",
            "- The combined model tests whether behavioral decay features add value beyond baseline customer history.",
            "- Logistic Regression is saved as a full preprocessing pipeline, so the scaler/imputer are included with the model.",
            "",
            "## Outputs",
            "",
        ]
    )
    for label, path in outputs.items():
        lines.append(f"- {label}: `{path}`")

    (REPORT_DIR / "phase4_modeling_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dirs()
    matrix = pd.read_pickle(FEATURE_MATRIX)
    matrix[TARGET_COL] = matrix[TARGET_COL].astype(bool)
    feature_groups = get_feature_groups(matrix)
    validate_matrix(matrix, feature_groups)

    train = matrix[matrix[SPLIT_COL] == "train"].copy()
    validation = matrix[matrix[SPLIT_COL] == "validation"].copy()
    test = matrix[matrix[SPLIT_COL] == "test"].copy()

    split_summary = (
        matrix.groupby(SPLIT_COL)[TARGET_COL]
        .agg(rows="count", positives="sum", positive_rate="mean")
        .reset_index()
    )

    results: dict[str, dict[str, dict[str, object]]] = {}
    validation_scores: dict[str, np.ndarray] = {}
    test_scores: dict[str, np.ndarray] = {}

    for feature_set, feature_cols in feature_groups.items():
        X_train = train[feature_cols]
        y_train = train[TARGET_COL]
        X_validation = validation[feature_cols]
        y_validation = validation[TARGET_COL]
        X_test = test[feature_cols]
        y_test = test[TARGET_COL]

        models = {
            "logistic_regression": fit_logistic(X_train, y_train),
            "xgboost": fit_xgboost(X_train, y_train),
        }
        results[feature_set] = {}

        for model_name, model in models.items():
            val_scores = predict_scores(model, X_validation)
            tst_scores = predict_scores(model, X_test)
            key = f"{feature_set}_{model_name}"
            validation_scores[key] = val_scores
            test_scores[key] = tst_scores
            results[feature_set][model_name] = {
                "validation": evaluate_predictions(y_validation, val_scores),
                "test": evaluate_predictions(y_test, tst_scores),
            }
            joblib.dump(model, MODEL_DIR / f"{key}.pkl")

    validation_predictions = PREDICTIONS_DIR / "phase4_validation_predictions.csv"
    test_predictions = PREDICTIONS_DIR / "phase4_test_predictions.csv"
    save_predictions(validation, validation_scores, validation_predictions)
    save_predictions(test, test_scores, test_predictions)

    outputs = {
        "feature_matrix": str(FEATURE_MATRIX),
        "validation_predictions": str(validation_predictions),
        "test_predictions": str(test_predictions),
        "models_dir": str(MODEL_DIR),
        "report_json": str(REPORT_DIR / "phase4_modeling_report.json"),
        "report_md": str(REPORT_DIR / "phase4_modeling_report.md"),
    }
    write_report(results, feature_groups, split_summary, outputs)

    print(
        json.dumps(
            {
                "matrix_rows": int(matrix.shape[0]),
                "feature_counts": {key: len(value) for key, value in feature_groups.items()},
                "split_summary": split_summary.to_dict(orient="records"),
                "report": str(REPORT_DIR / "phase4_modeling_report.md"),
            },
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
