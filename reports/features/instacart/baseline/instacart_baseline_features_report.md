# Instacart Baseline Feature Validation

## Scope

Built corrected peer baseline features against the current Phase 2 label contract. Censored-uncertain rows are excluded.

## Outputs

- Model-input feature table: `data/processed/instacart/features/instacart_baseline_features_model_input.pkl`
- Feature CSV inspection sample: `data/processed/instacart/features/instacart_baseline_features_model_input_sample.csv`

## Row Counts

- Behavior rows processed: 3,346,083
- Current label-eligible rows: 2,489,335
- Baseline feature rows: 2,489,335

## Feature Separation Summary

| Feature | Risk Direction | Risk-Decile Decay Rate | Lift | AUC |
|---|---:|---:|---:|---:|
| base_user_tenure_days | low | 26.72% | 1.50 | 0.566 |
| base_avg_reorder_ratio_to_date | low | 23.06% | 1.29 | 0.556 |
| base_avg_days_between_orders | low | 24.70% | 1.38 | 0.550 |
| base_avg_basket_size_to_date | low | 19.08% | 1.07 | 0.533 |
| base_total_orders_to_date | low | 19.68% | 1.10 | 0.525 |
| base_order_hour | high | 19.28% | 1.08 | 0.521 |
| base_order_dow | high | 17.68% | 0.99 | 0.501 |

## Notes

- `base_order_number` was removed because it duplicates `base_total_orders_to_date` in this snapshot design.
- `base_order_dow` and `base_order_hour` should be encoded as categorical or cyclical features for linear models.
- The feature file does not include target or label-status columns.
