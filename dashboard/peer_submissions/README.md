# Peer Dashboard Submission Archive

This folder preserves the peer-submitted dashboard files in their original form.

These originals are not the canonical dashboard code because they referenced older baseline-only artifacts that are not part of the synced project contract.

## Original Files

- `app_original.py`
- `screen2_customer_detail_original.py`

## Synced Counterparts

- `../app.py`
- `../screen1_risk_table.py`
- `../screen2_customer_detail.py`
- `../screen3_comparison.py`

## Compatibility Fixes Applied

- Replaced stale paths such as `baseline_model_predictions_full.csv`.
- Replaced CSV SHAP dependency with the current SHAP pickle output.
- Replaced root-level `orders_clean.csv` path with `data/processed/instacart/orders_clean.csv`.
- Added integration with the existing Screen 1 and Screen 3 modules.
- Kept the customer-detail intent, but aligned it with the leading-XGBoost operational risk model.
