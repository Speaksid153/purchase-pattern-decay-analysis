# Instacart Feature Matrix Validation

## Scope

Joined corrected leading features, corrected peer baseline features, and the Phase 2 target into one modeling-ready table.

## Outputs

- Feature matrix: `data/processed/instacart/features/instacart_feature_matrix.pkl`
- CSV inspection sample: `data/processed/instacart/features/instacart_feature_matrix_sample.csv`

## Source Counts

- Leading feature rows: 2,489,335
- Baseline feature rows: 2,489,335
- Target rows: 2,489,335
- Final feature matrix rows: 2,489,335
- Predictor columns: 45
- Leading predictor columns: 38
- Baseline predictor columns: 7

## Split Summary

| Split | Rows | Positive Rows | Positive Rate |
|---|---:|---:|---:|
| test | 372,458 | 66,538 | 17.86% |
| train | 1,742,232 | 311,148 | 17.86% |
| validation | 374,645 | 67,238 | 17.95% |

## Quality Checks

- Duplicate `user_id, order_id` rows: 0
- Forbidden predictor columns: []

## Modeling Notes

- Use `early_decay_label` as the target.
- Use `split` for train/validation/test separation.
- Treat `user_id` and `order_id` as keys only, not predictors.
- Encode `base_order_dow` and `base_order_hour` before linear models.
