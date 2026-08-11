# Phase 2 Churn Label Definition - Instacart

## Decision

Use a **future purchase-rhythm decay** label, not a generic 90-day churn label.

Final label: `early_decay_label = 1` when an eligible user-order snapshot is followed by:

- `next_gap_days >= 2x historical_median_gap_days`, because the next purchase is materially slower than the user's own normal rhythm.

`next_gap_days == 30` is not treated as an automatic positive label. It is used as a severity/ranking signal because Instacart caps long gaps at 30 days. The true gap may be 30 days or longer, but the cap alone does not prove churn.

Eligibility:

- The current order has basket behavior available.
- The next order gap is observed.
- The user's historical median gap is greater than 0.
- The snapshot has at least 3 known gaps up to the current order, including the current order's observed prior gap.
- The row is not censored-uncertain. If `next_gap_days == 30` but the user's 2x threshold is above 30 days, the true label cannot be observed because Instacart caps gaps at 30.

## Why Not 60/90/120-Day Churn

That would be the wrong label for Instacart. The dataset does not provide real calendar dates, and `days_since_prior_order` is capped at 30. A 90-day no-purchase label would sound professional but would not be measurable from this data.

## Final Label Counts

- Snapshot rows with current basket behavior: 3,346,083.
- Label-eligible rows: 2,489,335.
- Label-eligible users: 171,449.
- Early-decay positive rows: 444,924.
- Early-decay positive rate: 17.87%.
- Censored-uncertain rows excluded from supervised labeling: 104,579.
- Censored-uncertain users excluded from supervised labeling: 56,436.
- Rows hitting the 30-day cap: 120,796 (4.85%).

## Severity Tiers

| Tier | Rows |
|---|---:|
| normal | 1,813,763 |
| valid_decay_warning | 324,128 |
| watchlist | 230,648 |
| critical_capped_gap_fast_cadence | 69,483 |
| high_capped_gap | 51,313 |

Severity logic:

- `valid_decay_warning`: next gap is at least 2x the user's historical median.
- `high_capped_gap`: positive label and the observed next gap hits the 30-day cap.
- `critical_capped_gap_fast_cadence`: high capped gap where the user's normal median gap is 10 days or less.
- `watchlist`: not a final positive label, but shows a softer warning such as 1.5x slowdown or a capped 30-day gap.
- `censored_uncertain`: capped 30-day gap where the user's 2x threshold is above the observable range; excluded from supervised labels.
- `normal`: eligible row without a material future slowdown.


## Modeling Split

The label table includes a deterministic user-level split. This avoids putting the same user into train and test, which would inflate performance.

| Split | Rows | Positive rows | Positive rate |
|---|---:|---:|---:|
| test | 372,458 | 66,538 | 17.86% |
| train | 1,742,232 | 311,148 | 17.86% |
| validation | 374,645 | 67,238 | 17.95% |

## Sensitivity Analysis

| Rule | Min known gaps | Eligible rows | Positive rows | Positive rate | Censored uncertain rows excluded | Eligible users |
|---|---:|---:|---:|---:|---:|---:|
| next_gap_eq_30 | 2 | 2,799,979 | 274,247 | 9.79% | 0 | 206,162 |
| next_gap_ge_1.5x_historical_median | 2 | 2,702,228 | 761,442 | 28.18% | 97,751 | 194,327 |
| next_gap_ge_2.0x_historical_median | 2 | 2,658,816 | 475,604 | 17.89% | 141,163 | 190,641 |
| next_gap_ge_2.5x_historical_median | 2 | 2,622,745 | 279,281 | 10.65% | 177,234 | 189,457 |
| hybrid_next_gap_30_or_2x_median | 2 | 2,799,979 | 616,767 | 22.03% | 0 | 206,162 |
| next_gap_eq_30 | 3 | 2,593,914 | 225,375 | 8.69% | 0 | 182,171 |
| next_gap_ge_1.5x_historical_median | 3 | 2,522,031 | 708,268 | 28.08% | 71,883 | 172,890 |
| next_gap_ge_2.0x_historical_median | 3 | 2,489,335 | 444,924 | 17.87% | 104,579 | 171,449 |
| next_gap_ge_2.5x_historical_median | 3 | 2,457,186 | 260,512 | 10.60% | 136,728 | 170,173 |
| hybrid_next_gap_30_or_2x_median | 3 | 2,593,914 | 549,503 | 21.18% | 0 | 182,171 |
| next_gap_eq_30 | 5 | 2,249,519 | 155,443 | 6.91% | 0 | 146,433 |
| next_gap_ge_1.5x_historical_median | 5 | 2,213,954 | 616,213 | 27.83% | 35,565 | 141,440 |
| next_gap_ge_2.0x_historical_median | 5 | 2,191,251 | 386,257 | 17.63% | 58,268 | 140,236 |
| next_gap_ge_2.5x_historical_median | 5 | 2,166,573 | 224,396 | 10.36% | 82,946 | 139,292 |
| hybrid_next_gap_30_or_2x_median | 5 | 2,249,519 | 444,525 | 19.76% | 0 | 146,433 |
| next_gap_eq_30 | 9 | 1,739,085 | 78,512 | 4.51% | 0 | 101,675 |
| next_gap_ge_1.5x_historical_median | 9 | 1,732,640 | 475,255 | 27.43% | 6,445 | 100,435 |
| next_gap_ge_2.0x_historical_median | 9 | 1,723,232 | 297,775 | 17.28% | 15,853 | 99,737 |
| next_gap_ge_2.5x_historical_median | 9 | 1,709,911 | 172,679 | 10.10% | 29,174 | 99,118 |
| hybrid_next_gap_30_or_2x_median | 9 | 1,739,085 | 313,628 | 18.03% | 0 | 101,675 |

## Leakage Rules For Phase 4

- Use `early_decay_label` as the target.
- Use `decay_severity_score`, `decay_severity_tier`, and `gap_cap_30_flag` for ranking/intervention analysis, not as direct model features unless you are intentionally building a post-model prioritization layer.
- Use only rows where `label_eligible == True`.
- Keep `label_status == 'censored_uncertain'` rows out of supervised training and final test metrics.
- Do not use `next_order_id`, `next_order_number`, `next_eval_set`, `next_gap_days`, or any label columns as features.
- Do not use `user_id` as a model feature.
- Use the provided `split` column unless you intentionally run a separate time-style experiment.

## Output

- `data/processed/instacart/labels/instacart_phase2_decay_labels.csv`
