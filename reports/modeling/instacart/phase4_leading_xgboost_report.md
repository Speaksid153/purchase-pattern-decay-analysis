# Phase 4 Leading XGBoost Report

## Scope

Focused Phase 4 deliverable for the behavioral leading-indicator model. This uses only leading feature columns from the master feature matrix and trains XGBoost with class imbalance handling.

## Important Split Caveat

Instacart does not provide global calendar dates. The requested real time-based split is not directly possible. The implemented split is a user-level relative-time proxy: users are sorted by their latest eligible `relative_day`, then split into earlier train, middle validation, and later test groups. This preserves user separation and avoids random row splitting.

## Input

- Master feature matrix rows: 2,489,335
- Leading feature columns: 38

## Split Summary

| Split | Rows | Users | Positives | Positive Rate |
|---|---:|---:|---:|---:|
| test | 1,075,413 | 25,718 | 156,767 | 14.58% |
| train | 833,721 | 120,014 | 178,652 | 21.43% |
| validation | 580,201 | 25,717 | 109,505 | 18.87% |

## Test Metrics

- ROC-AUC: 0.6607
- PR-AUC: 0.2585
- Top 5% lift: 2.46x
- Top 10% lift: 2.13x
- Precision at validation top-10% threshold: 35.53%
- Recall at validation top-10% threshold: 12.68%

## Timing Metric

- Positive-event users in test: 23,892
- Correctly flagged positive-event users: 5,203
- Correctly flagged user rate: 21.78%
- Median days before label-defined decay threshold: 12.00
- Mean days before label-defined decay threshold: 24.65
- Median days before next observed order: 18.00
- Mean days before next observed order: 29.47

## Best Hyperparameters

```json
{
  "n_estimators": 220,
  "max_depth": 6,
  "learning_rate": 0.06,
  "subsample": 0.85,
  "colsample_bytree": 0.9,
  "scale_pos_weight": 2.3833757808476816,
  "weight_multiplier": 0.65,
  "min_child_weight": 3,
  "reg_lambda": 2.0
}
```

## Outputs

- trained_model: `models/phase4/leading_xgboost_time_proxy.pkl`
- test_predictions: `data/processed/instacart/predictions/leading_xgboost_time_proxy_test_predictions.csv`
- test_shap_values: `data/processed/instacart/predictions/leading_xgboost_time_proxy_test_shap_values.pkl`
- report_md: `reports/modeling/instacart/phase4_leading_xgboost_report.md`
- report_json: `reports/modeling/instacart/phase4_leading_xgboost_report.json`
