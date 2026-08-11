# Peer Phase 3 Baseline Feature Review

## Files Reviewed

- `C:/Users/Siddharth/Downloads/phase3 report.md`
- `C:/Users/Siddharth/Downloads/baseline_features_phase3.ipynb`
- `C:/Users/Siddharth/Downloads/baseline_features.csv`

## Executive Verdict

The peer baseline feature work is directionally useful and mostly leakage-safe, but it is **not ready to merge as-is** because it was built against the older Phase 2 label contract.

Update after integration: the peer baseline idea has now been merged through a corrected project script:

```text
scripts/build_validate_baseline_features_instacart.py
```

The corrected baseline output is:

```text
data/processed/instacart/features/instacart_baseline_features_model_input.pkl
```

The final combined matrix is:

```text
data/processed/instacart/features/instacart_feature_matrix.pkl
```

The main issue is row eligibility:

- Peer baseline rows: **2,593,914**
- Current corrected supervised-label rows: **2,489,335**
- Rows that must now be excluded: **104,579**

Those 104,579 rows are the censored-uncertain 30-day-cap cases that we removed from supervised training/evaluation. They are present in the peer baseline CSV, so the peer file must be filtered or regenerated before modeling.

## Compatibility Check Against Current Project

The peer CSV joins cleanly to our current label file by `user_id, order_id`.

| Check | Result |
|---|---:|
| Peer baseline rows | 2,593,914 |
| Duplicate `user_id, order_id` rows | 0 |
| Duplicate `order_id` rows | 0 |
| Rows found in current label table | 2,593,914 |
| Rows currently label-eligible | 2,489,335 |
| Rows now censored-uncertain | 104,579 |

After filtering to `label_eligible == True`, the peer baseline feature file has the correct modeling row count:

| Split | Rows |
|---|---:|
| train | 1,742,232 |
| validation | 374,645 |
| test | 372,458 |

## Feature Columns

Peer baseline columns:

- `base_user_tenure_days`
- `base_order_number`
- `base_total_orders_to_date`
- `base_avg_days_between_orders`
- `base_avg_basket_size_to_date`
- `base_avg_reorder_ratio_to_date`
- `base_order_dow`
- `base_order_hour`

The column naming is good because baseline features use the `base_` prefix and will not collide with our leading-feature names.

## Leakage Review

The baseline CSV itself does not include obvious leaked target/future columns.

No leaked columns found:

- no `early_decay_label`
- no `label_eligible`
- no `next_gap_days`
- no `next_order_id`
- no severity columns

However, the notebook has one important handoff risk:

```python
eligible_keys = labels[['user_id', 'order_id']]
baseline_features = baseline_features.merge(eligible_keys, on=['user_id', 'order_id'], how='inner')
assert len(baseline_features) == len(labels)
```

This assumes the label file already contains only modeling-eligible rows. In our current project, `instacart_phase2_decay_labels.csv` contains all label statuses, including `not_label_eligible` and `censored_uncertain`.

Correct logic should filter first:

```python
eligible_keys = labels.loc[
    labels['label_eligible'] == True,
    ['user_id', 'order_id']
]
```

or join directly to:

```text
data/processed/instacart/features/instacart_leading_feature_targets.pkl
```

## Code Path Issues

The notebook references:

```python
orders_clean = pd.read_csv('orders_clean.csv')
order_behavior = pd.read_csv('order_behavior_base.csv')
```

Those are not the current project paths. In our repo, the correct files are:

```text
data/processed/instacart/orders_clean.csv
data/processed/instacart/user_order_behavior_base.csv
```

This matters because another person running the notebook from the project root may fail or accidentally use stale local files.

## Baseline Feature Signal Check

After joining peer baseline features to the corrected current target table, the strongest standalone baseline signals are:

| Feature | Risk Direction | AUC | Top-Risk Decile Rate | Lift |
|---|---:|---:|---:|---:|
| `base_user_tenure_days` | low | 0.566 | 26.72% | 1.50 |
| `base_avg_reorder_ratio_to_date` | low | 0.556 | 23.06% | 1.29 |
| `base_avg_days_between_orders` | low | 0.550 | 24.70% | 1.38 |
| `base_avg_basket_size_to_date` | low | 0.533 | 19.08% | 1.07 |
| `base_order_number` | low | 0.525 | 19.68% | 1.10 |
| `base_order_hour` | high | 0.521 | 19.28% | 1.08 |
| `base_order_dow` | high | 0.501 | 17.68% | 0.99 |

Interpretation:

- The baseline is not weak. `base_user_tenure_days` is almost as strong as our best leading feature on standalone AUC.
- This is useful because it makes the final comparison more credible. The leading model must beat a real baseline, not a strawman.
- `base_order_dow` is basically noise as a standalone predictor.
- `base_order_number` and `base_total_orders_to_date` are duplicates in this snapshot setup. Keep one, not both, unless the peer has a specific reason to keep both.

## Comparison With Our Leading Features

Our strongest leading feature:

| Feature | AUC | Top-Risk Decile Rate | Lift |
|---|---:|---:|---:|
| `current_gap_ratio_to_historical_median` | 0.575 | 34.04% | 1.90 |

Peer's strongest baseline feature:

| Feature | AUC | Top-Risk Decile Rate | Lift |
|---|---:|---:|---:|
| `base_user_tenure_days` | 0.566 | 26.72% | 1.50 |

This means the baseline is competitive. The project should not claim that leading features obviously dominate before modeling. The right claim is:

> Baseline features capture broad customer maturity and habitual intensity, while leading features capture recent behavioral slowdown. The modeling phase should test whether leading decay signals add incremental lift over the baseline.

## Required Fixes Before Merge

1. Filter peer baseline features to the corrected target table.

Use only rows present in:

```text
data/processed/instacart/features/instacart_leading_feature_targets.pkl
```

2. Update notebook paths.

Use:

```text
data/processed/instacart/orders_clean.csv
data/processed/instacart/user_order_behavior_base.csv
data/processed/instacart/labels/instacart_phase2_decay_labels.csv
```

3. Remove one duplicate order-count feature.

`base_order_number` and `base_total_orders_to_date` are identical in this row design. Keep `base_total_orders_to_date` for readability.

4. Add split or join to target file during modeling.

The baseline feature CSV does not include `split`, so modeling must join to the target file by `user_id, order_id`.

5. Treat `base_order_dow` and `base_order_hour` as categorical/time features.

Do not feed them into logistic regression as plain continuous numbers without encoding. Use one-hot, cyclical sine/cosine, or tree-based models that can tolerate integer-coded categories better.

## Final Recommendation

Accept the peer's baseline feature idea, but do not merge the current CSV directly.

Best next step:

1. Peer reruns the notebook against the corrected Phase 2 label output.
2. Baseline output is filtered to **2,489,335** rows.
3. Duplicate `base_order_number` / `base_total_orders_to_date` is removed.
4. Baseline features are joined with our target file during modeling.
5. Model comparison is run as:

| Model | Feature Set |
|---|---|
| Logistic Regression | baseline only |
| Logistic Regression | leading only |
| Logistic Regression | baseline + leading |
| Tree/boosting model | baseline only |
| Tree/boosting model | leading only |
| Tree/boosting model | baseline + leading |

That comparison will answer the real project question: whether behavioral decay features add value beyond traditional baseline customer-history features.
