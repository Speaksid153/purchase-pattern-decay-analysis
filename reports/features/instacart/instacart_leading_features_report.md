# Instacart Leading Feature Validation

## Scope

Built leakage-safe behavioral decay features from current and historical user-order behavior. The future label is used only for validation.

## Outputs

- Model-input feature table: `C:\Users\Siddharth\Documents\Early Churn Predictior\data\processed\instacart\features\instacart_leading_features_model_input.pkl`
- Target table: `C:\Users\Siddharth\Documents\Early Churn Predictior\data\processed\instacart\features\instacart_leading_feature_targets.pkl`
- Feature CSV inspection sample: `C:\Users\Siddharth\Documents\Early Churn Predictior\data\processed\instacart\features\instacart_leading_features_model_input_sample.csv`
- Target CSV inspection sample: `C:\Users\Siddharth\Documents\Early Churn Predictior\data\processed\instacart\features\instacart_leading_feature_targets_sample.csv`
- Plots: `C:\Users\Siddharth\Documents\Early Churn Predictior\reports\features\instacart\plots`

## Row Counts

- Behavior rows processed: 3,346,083
- Label rows available: 3,346,083
- Label-eligible rows used for validation: 2,489,335
- Feature columns created: 38

## Feature Separation Summary

| Feature | Risk Direction | Retained Median | Decay Median | Risk-Decile Decay Rate | Lift | AUC |
|---|---:|---:|---:|---:|---:|---:|
| current_gap_ratio_to_historical_median | high | 1.000 | 1.000 | 34.04% | 1.90 | 0.575 |
| latest_gap_ratio_to_prior_avg | high | 0.856 | 0.887 | 31.78% | 1.78 | 0.533 |
| gap_slope_last3 | high | 0.000 | 0.000 | 24.63% | 1.38 | 0.524 |
| purchase_frequency_slope_last3 | low | 0.000 | 0.000 | 21.34% | 1.21 | 0.519 |
| item_count_recent3_ratio_to_prior | low | 0.989 | 0.979 | 19.64% | 1.10 | 0.511 |
| distinct_aisle_count_recent3_ratio_to_prior | low | 0.997 | 0.988 | 19.60% | 1.10 | 0.509 |
| distinct_department_count_recent3_ratio_to_prior | low | 1.000 | 1.000 | 19.49% | 1.09 | 0.508 |
| latest_gap_ratio_to_previous_gap | high | 1.000 | 1.000 | 23.11% | 1.30 | 0.508 |
| dow_distance_from_prior_pattern | high | 1.319 | 1.343 | 17.97% | 1.01 | 0.505 |
| hour_distance_from_prior_pattern | high | 2.563 | 2.564 | 18.14% | 1.01 | 0.501 |
| reorder_ratio_slope_last3 | low | 0.000 | 0.000 | 19.06% | 1.07 | 0.495 |
| reorder_ratio_recent3_delta_from_prior | low | 0.152 | 0.157 | 17.59% | 0.98 | 0.489 |
| history_reliability_score | high | 1.000 | 1.000 | 17.28% | 0.97 | 0.485 |

## Practical Read

- Features with AUC close to 0.50 have weak standalone separation and should not be oversold.
- Gap/cadence features are expected to be strongest because the Phase 2 label is also purchase-rhythm based.
- Basket, reorder, category, and time-consistency features are still useful if they add incremental signal in a multivariate model.

## Leakage Control

Feature generation uses current and historical order behavior only. The historical median gap is reused from Phase 2 snapshot metadata, but target labels and next_gap columns are used only after feature creation for validation plots/statistics. Model-input feature files are saved without early_decay_label, label_eligible, label_status, or split; split lives in the target table.
