# Phase 4 Peer Sync Fix

## What Was Wrong

The peer Phase 4 notebook modeled from `baseline_features.csv` and then merged labels separately. That created a row mismatch against the corrected Phase 2/3 contract.

Peer validation set:

- Rows: 390,067
- Positives: 67,238

Correct synced validation set:

- Rows: 374,645
- Positives: 67,238

The extra 15,422 validation rows were not part of the final corrected modeling matrix and would dilute the churn rate by adding extra non-positive rows.

## Fix Applied

Phase 4 now uses one source of truth:

`data/processed/instacart/features/instacart_feature_matrix.pkl`

The script derives three feature sets from that one table:

- Baseline-only: 7 peer baseline predictors
- Leading-only: 38 behavioral decay predictors
- Combined: all 45 predictors

## Synced Outputs

- Script: `scripts/phase4_modeling_instacart.py`
- Notebook: `notebooks/07_phase4_modeling_instacart.ipynb`
- Report: `reports/modeling/instacart/phase4_modeling_report.md`
- Validation predictions: `data/processed/instacart/predictions/phase4_validation_predictions.csv`
- Test predictions: `data/processed/instacart/predictions/phase4_test_predictions.csv`
- Models: `models/phase4/`

## Current Best Result

Best validation model by PR-AUC:

- Feature set: combined
- Model: XGBoost
- Validation ROC-AUC: 0.7206
- Validation PR-AUC: 0.3599
- Validation top-5% lift: 2.71x

## Practical Interpretation

The corrected comparison supports the project thesis. Baseline-only XGBoost is useful, but leading behavioral decay features improve ranking quality substantially. The combined model performs best, which means the decay signals add value beyond traditional baseline customer-history features.
