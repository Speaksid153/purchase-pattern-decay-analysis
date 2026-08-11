# Project Validation Summary

Validation date: 2026-08-11

## Scope

Checked the complete labeling, feature engineering, modeling, API, dashboard, and deployment workflow after the public portfolio release.

## Code And Notebook Checks

- Python scripts compiled successfully: 15
- Jupyter notebooks parsed successfully: 8
- TypeScript checking, production bundling, API contracts, and serving-bundle tests passed.

## Master Matrix Contract

- Leading feature rows: 2,489,335
- Baseline feature rows: 2,489,335
- Target rows: 2,489,335
- Final feature matrix rows: 2,489,335
- Final feature matrix columns: 49
- Leading predictors: 38
- Baseline predictors: 7
- Predictor overlap between leading and baseline sets: none
- Duplicate `user_id, order_id` keys: 0
- Metadata leakage columns in final matrix (`eval_set`, `order_number`): none

## Label Contract

- Target: `early_decay_label`
- Positive rows: 444,924
- Positive rate: 17.87%

## Standard Project Split

| Split | Rows |
|---|---:|
| train | 1,742,232 |
| validation | 374,645 |
| test | 372,458 |

## Phase 4 Outputs

Standard Phase 4 comparison predictions:

- Validation predictions: 374,645 rows
- Test predictions: 372,458 rows
- Risk-score columns: baseline logistic regression, baseline XGBoost, leading logistic regression, leading XGBoost, combined logistic regression, combined XGBoost

Focused leading XGBoost deliverable:

- Test predictions: 1,075,413 rows
- SHAP matrix: 1,075,413 rows
- Duplicate prediction keys: 0
- Duplicate SHAP keys: 0

## Current Modeling Reports

- `reports/modeling/instacart/phase4_modeling_report.md`
- `reports/modeling/instacart/phase4_leading_xgboost_report.md`

## GitHub Hygiene

Large and derived files are intentionally ignored:

- `data/`
- `models/`
- `outputs/`
- `__pycache__/`
- generated JSON reports and non-curated diagnostic plots

Canonical reports, eight notebooks, reproducible scripts, and selected analytical plots are kept in the project tree for review.
