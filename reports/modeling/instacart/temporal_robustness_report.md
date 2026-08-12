# Temporal Robustness Experiment

## Decision

- Replacement promoted: **yes**
- Selected development candidate: `current_leading_row`
- Selected feature count: 38
- Selection used two rolling development folds; the final 15% user cohort remained untouched until this decision.

## Untouched Test Comparison

| Metric | Previous model | Candidate | Change |
|---|---:|---:|---:|
| Row ROC-AUC | 0.6607 | 0.6640 | +0.0034 |
| Row PR-AUC | 0.2585 | 0.2637 | +0.0052 |
| Latest-customer ROC-AUC | 0.6604 | 0.6707 | +0.0103 |
| Latest-customer PR-AUC | 0.2650 | 0.2750 | +0.0100 |

## Rolling Development Results

| Candidate | Features | Weighting | Mean ROC-AUC | Mean PR-AUC | Latest ROC-AUC | Latest PR-AUC |
|---|---:|---|---:|---:|---:|---:|
| `current_leading_row` | 38 | row | 0.7237 | 0.3706 | 0.7968 | 0.5030 |
| `regularized_leading_row` | 38 | row | 0.7236 | 0.3702 | 0.7965 | 0.5023 |
| `regularized_combined_row` | 45 | row | 0.7201 | 0.3673 | 0.7957 | 0.4992 |
| `regularized_drift_robust_user_recency` | 38 | user_recency | 0.7211 | 0.3659 | 0.7966 | 0.5012 |
| `regularized_combined_user_recency` | 45 | user_recency | 0.7178 | 0.3629 | 0.7963 | 0.5021 |
| `regularized_leading_user` | 38 | user | 0.7188 | 0.3611 | 0.7959 | 0.5009 |
| `regularized_combined_user` | 45 | user | 0.7177 | 0.3613 | 0.7960 | 0.5006 |
| `regularized_change_only_user_recency` | 23 | user_recency | 0.7060 | 0.3519 | 0.7807 | 0.4936 |

## Interpretation

The experiment targets lifecycle distribution shift rather than optimizing against the held-out test. User-balanced weighting makes each customer contribute equal total training weight; recency weighting emphasizes later development histories; drift-robust feature sets are selected using development folds only.

The more complex regularized, combined-feature, user-balanced, and recency-weighted designs did not outperform the original leading-feature family across the rolling folds. The promoted gain therefore comes from more defensible temporal selection and retraining on all development rows—not from claiming that added complexity solved the dataset's lifecycle shift. The row-level ROC-AUC gain is small; the clearer improvement is at the latest-customer decision point.
