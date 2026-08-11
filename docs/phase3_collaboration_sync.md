# Phase 3 Collaboration Sync

## Purpose

From Phase 3 onward, the work can split, but only if the interfaces are agreed upfront.

The biggest risk is not model difficulty. The biggest risk is that both people build reasonable pieces that do not join cleanly because of different label files, split logic, feature keys, or leakage assumptions.

Use this document as the pre-Phase 3 alignment checklist.

## 1. Final Label Contract

Confirm the exact Phase 2 label before building features.

Final target:

```text
early_decay_label = 1
if next_gap_days >= 2.0 x historical_median_gap_days
```

Eligibility:

```text
label_eligible == True
```

This means:

- The current order has basket behavior available.
- The next order gap is observed.
- The user has a valid historical median gap.
- The snapshot has at least 3 known gaps up to the current order, including the current order's observed prior gap.
- The row is not censored-uncertain.

Important:

- `next_gap_days == 30` is a severity/ranking signal, not the target.
- If `next_gap_days == 30` and the user's 2x threshold is above 30 days, the row is censored-uncertain and excluded from supervised training/evaluation.
- The target is purchase-rhythm decay, not literal permanent churn.

## 2. Shared Base Table

Both people should use the same input file:

```text
data/processed/instacart/labels/instacart_phase2_decay_labels.csv
```

Use only rows where:

```text
label_eligible == True
```

Do not create separate label files unless both people agree and document the change.

## 3. Train / Validation / Test Split

Use the existing `split` column from the label file.

Do not create a random split separately.

Split usage:

| split | purpose |
|---|---|
| train | model fitting |
| validation | threshold choice, tuning, model selection |
| test | final untouched evaluation |

Reason:

The split is user-level, so the same user should not appear in multiple modeling splits.

## 4. Feature Ownership

Agree ownership before coding.

Recommended split:

| owner | feature family |
|---|---|
| Sid | leading behavioral decay features |
| Shreya  | baseline/traditional behavior features |

### Sid: Leading Features

Examples:

- gap acceleration
- basket shrinkage
- reorder-routine change
- department/category narrowing
- recent behavior vs historical behavior
- ranking/intervention support features

### Shreya: Baseline Features

Examples:

- total orders to date
- average basket size to date
- average reorder ratio to date
- average days between orders
- user tenure / relative age
- day-of-week and hour-of-day ordering patterns
- traditional recency/frequency-style features

## 5. Output Format

Each feature file should return one row per eligible user-order snapshot.

Required keys:

```text
user_id
order_id
```

Recommended outputs:

```text
data/processed/instacart/features/instacart_leading_features_model_input.pkl
data/processed/instacart/features/instacart_leading_feature_targets.pkl
data/processed/instacart/features/instacart_baseline_features_model_input.pkl
data/processed/instacart/features/instacart_feature_matrix.pkl
data/processed/instacart/features/instacart_leading_features_model_input_sample.csv
data/processed/instacart/features/instacart_leading_feature_targets_sample.csv
data/processed/instacart/features/instacart_baseline_features_model_input_sample.csv
data/processed/instacart/features/instacart_feature_matrix_sample.csv
```

Hard requirements:

- No duplicate `user_id, order_id` pairs.
- Feature files must join cleanly to the label table.
- The model-input feature file must not include `early_decay_label`, `label_eligible`, or `label_status`.
- The target file should carry `user_id`, `order_id`, `split`, and `early_decay_label`.
- The final matrix should have exactly `2,489,335` rows unless the Phase 2 label contract is intentionally changed.

## 6. Feature Naming Rules

Use descriptive feature names and check for collisions before merging. The current implemented leading-feature file does not use a `lead_` prefix, so do not assume prefixed columns exist.

Examples of current leading-feature names:

```text
current_gap_ratio_to_historical_median
latest_gap_ratio_to_prior_avg
item_count_recent3_ratio_to_prior
distinct_aisle_count_recent3_ratio_to_prior
history_reliability_score
```

## 7. Leakage Rules

These columns must not be used as model features:

```text
next_order_id
next_order_number
next_eval_set
next_gap_days
next_gap_ratio_to_historical_median
early_decay_label
label_eligible
label_status
next_gap_30d_label
gap_cap_30_flag
next_gap_1_5x_median_label
next_gap_2x_median_label
next_gap_2_5x_median_label
decay_severity_score
decay_severity_tier
label_definition
```

Also do not use:

```text
user_id
order_id
```

as model features. They are keys only.

Use severity fields only after prediction for ranking/intervention analysis, unless a separate prioritization layer is intentionally being built and documented.

## 8. Modeling Comparison Design

Do not compare:

```text
XGBoost + leading features
vs
Logistic regression + baseline features
```

That comparison mixes feature quality with model quality.

Better comparison:

| model | feature set |
|---|---|
| Logistic Regression | baseline features |
| Logistic Regression | leading features |
| XGBoost | baseline features |
| XGBoost | leading features |

This lets the project answer the real question:

> Do leading behavioral decay features improve early risk detection compared with traditional baseline features?

## 9. Evaluation Metrics

Agree metrics before modeling.

Use:

- ROC-AUC
- PR-AUC
- precision and recall at selected threshold
- confusion matrix
- lift in top 5% and top 10% highest-risk snapshots
- calibration check

For the business story, also report:

- top risk drivers
- severity tier distribution among high-risk predictions
- example user-level explanations

## 10. Intervention Mapping

Model output should connect to business actions.

Suggested mapping:

| signal | intervention idea |
|---|---|
| high gap acceleration | reorder reminder |
| basket shrinkage | bundle or cart-building incentive |
| reorder-routine decline | one-click reorder prompt |
| department/category narrowing | category-specific offer |
| high capped-gap fast cadence | stronger win-back action |

## 11. Proposed File Structure

Recommended structure:

```text
src/
  features/
    build_leading_features.py
    build_baseline_features.py
    build_feature_matrix.py
  models/
    train_logistic.py
    train_xgboost.py
    evaluate_models.py

data/processed/instacart/features/
  instacart_leading_features_model_input.pkl
  instacart_leading_feature_targets.pkl
  instacart_baseline_features_model_input.pkl
  instacart_feature_matrix.pkl
  instacart_leading_features_model_input_sample.csv
  instacart_leading_feature_targets_sample.csv
  instacart_baseline_features_model_input_sample.csv
  instacart_feature_matrix_sample.csv

reports/modeling/
```

## 12. Merge Checkpoint Before Modeling

Before Phase 4, verify:

- row counts match expectations
- no duplicate `user_id, order_id`
- no leaked columns
- no column name conflicts
- feature matrix joins cleanly
- train/validation/test label rates are stable
- both people can explain every feature they created

## Open Decisions

Discuss and write down final answers:

| decision | answer |
|---|---|
| Final label file |  |
| Minimum history rule |  |
| Feature ownership |  |
| Final feature file paths |  |
| Model families to compare |  |
| Primary evaluation metric |  |
| Threshold-selection rule |  |
| Intervention categories |  |

## Non-Negotiable

If the label, split, or feature keys change, both people need to know before continuing.

Otherwise, Phase 4 will become join debugging and leakage cleanup instead of modeling.
