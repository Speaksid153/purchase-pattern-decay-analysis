# Peer Phase 5 Dashboard Submission

This folder archives the peer's original Phase 5 dashboard notes.

## Compatibility Finding

The submitted dashboard direction was useful, but the files were not directly compatible with the synced project because they referenced old baseline-only prediction and SHAP files:

- `data/processed/instacart/predictions/baseline_model_predictions_full.csv`
- `data/processed/instacart/shap/xgboost_baseline_shap_values_full.csv`
- root-level `orders_clean.csv`

Those are not the current Phase 4 artifacts.

## Synced Resolution

The project dashboard now uses current artifacts:

- `data/processed/instacart/predictions/leading_xgboost_time_proxy_test_predictions.csv`
- `data/processed/instacart/predictions/leading_xgboost_time_proxy_test_shap_values.pkl`
- `data/processed/instacart/predictions/phase4_validation_predictions.csv`
- `data/processed/instacart/predictions/phase4_test_predictions.csv`
- `data/processed/instacart/labels/instacart_phase2_decay_labels.csv`

Canonical dashboard files:

- `dashboard/app.py`
- `dashboard/screen1_risk_table.py`
- `dashboard/screen2_customer_detail.py`
- `dashboard/screen3_comparison.py`
