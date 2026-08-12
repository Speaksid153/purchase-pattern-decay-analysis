# Phase 4 Temporally Robust XGBoost Report

## Scope

Promoted model selected across two rolling user-lifecycle development folds, then evaluated once on the untouched final 15% user cohort.

## Test Metrics

- ROC-AUC: 0.6640
- PR-AUC: 0.2637
- Top 5% lift: 2.53x
- Top 10% lift: 2.18x
- Latest-customer ROC-AUC: 0.6707
- Latest-customer PR-AUC: 0.2750
- Precision at rolling-development threshold: 36.01%
- Recall at rolling-development threshold: 13.81%

## Timing Metric

- Correctly flagged users: 5,500 / 23,892
- Correctly flagged user rate: 23.02%
- Median lead time: 12.0 days

## Selected Design

- Candidate: `current_leading_row`
- Features: 38
- Weighting: `row`
- Regularization profile: `current`

See `reports/modeling/instacart/temporal_robustness_report.md` for all development candidates and the honest pre/post comparison.
