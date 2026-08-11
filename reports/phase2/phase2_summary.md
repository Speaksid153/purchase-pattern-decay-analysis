# Phase 2 - Churn / Decay Label Definition

## Step 1: Ratio-Based Churn Thresholds

| ratio_multiplier | eligible_rows | churn_count | churn_rate_pct |
|---:|---:|---:|---:|
| 1.50 | 2,522,031 | 708,268 | 28.08 |
| 2.00 | 2,489,335 | 444,924 | 17.87 |
| 2.50 | 2,457,186 | 260,512 | 10.60 |

## Step 1b: 30-Day Cap Check

Instacart caps `days_since_prior_order` at 30, so `next_gap_days == 30` means the true gap is **30 days or longer**.

| cap_condition | eligible_rows | capped_gap_count | capped_gap_rate_pct |
|---|---:|---:|---:|
| next_gap_days == 30 among labeled rows | 2,489,335 | 120,796 | 4.85 |

Important: we are **not** treating the 30-day cap as an automatic churn label. We use it as a severity/ranking signal.

Additional censoring fix: rows where `next_gap_days == 30` but the user's 2x threshold is above 30 days are excluded from supervised labeling because the true outcome is not observable. This removed **104,579** censored-uncertain rows.

## Step 2: Final Working Definition

Chosen working definition:

- Churn/decay warning if `next_gap_days >= 2.0 x historical_median_gap_days`
- Require at least `3` known historical gaps before labeling
- Use `next_gap_days == 30` only as a severity flag, not as the main label

Result:

| metric | value |
|---|---:|
| total behavior snapshots | 3,346,083 |
| label-eligible rows | 2,489,335 |
| label-eligible users | 171,449 |
| churn/decay warning count | 444,924 |
| churn/decay warning rate | 17.87% |
| censored-uncertain rows excluded | 104,579 |

## Step 3: Severity Ranking Scheme

After labeling, we rank users/snapshots so that the model output can support business action, not just binary classification.

The final label answers:

> Is this a valid behavioral decay warning?

The ranking scheme answers:

> How serious is this warning, and how urgently should the business act?

### Ranking Inputs

| input | meaning | why it matters |
|---|---|---|
| `next_gap_ratio_to_historical_median` | `next_gap_days / historical_median_gap_days` | Measures how abnormal the next gap is for that specific user. |
| `gap_cap_30_flag` | Whether `next_gap_days == 30` | Indicates capped/uncertain long inactivity; true gap may be longer than 30. |
| `known_gap_count_to_date` | Number of known gaps available before labeling | More history makes the user's normal rhythm more reliable. |
| `historical_median_gap_days` | User's normal purchase cadence | A 30-day gap is more severe for a weekly buyer than for a monthly buyer. |

### Severity Score

Severity score logic:

```text
severity_score =
  clipped(next_gap_ratio_to_historical_median, 0, 5)
  x history_reliability_weight
  + cap_boost
```

History reliability weight:

| known_gap_count_to_date | reliability_weight |
|---:|---:|
| 3-4 gaps | 0.70 |
| 5-8 gaps | 0.85 |
| 9+ gaps | 1.00 |

Cap boost:

| condition | cap_boost |
|---|---:|
| `next_gap_days == 30` | 0.50 |
| otherwise | 0.00 |

This prevents the 30-day cap from becoming an automatic label, but still ranks capped-gap users higher when prioritizing interventions.

### Severity Tiers

| severity_tier | rows | interpretation |
|---|---:|---|
| normal | 1,813,763 | No meaningful future slowdown. |
| watchlist | 230,648 | Softer warning, such as 1.5x slowdown or capped 30-day gap, but not final churn label. |
| valid_decay_warning | 324,128 | Next gap is at least 2x the user's historical median gap. |
| high_capped_gap | 51,313 | Valid decay warning and next gap hits the 30-day cap. |
| critical_capped_gap_fast_cadence | 69,483 | Valid decay warning, 30-day cap, and user normally buys frequently. |

### How To Use The Ranking

Suggested action mapping:

| severity_tier | suggested action |
|---|---|
| normal | No intervention. |
| watchlist | Light-touch reminder or passive recommendation. |
| valid_decay_warning | Personalized reorder prompt or category-specific nudge. |
| high_capped_gap | Stronger reactivation offer or personalized basket recovery. |
| critical_capped_gap_fast_cadence | Highest-priority win-back action; user has broken a frequent purchase habit. |

## Step 4: Train / Validation / Test Split

User-level split, so the same user does not appear in multiple splits.

| split | rows | churn_count | churn_rate_pct |
|---|---:|---:|---:|
| train | 1,742,232 | 311,148 | 17.86 |
| validation | 374,645 | 67,238 | 17.95 |
| test | 372,458 | 66,538 | 17.86 |

## Final Label Justification

We are not using a normal 60/90/120-day churn window because Instacart has no real calendar dates and gaps are capped at 30 days.

Instead, we define churn as **future purchase-rhythm decay**:

> A user is flagged when their next purchase gap becomes at least 2x longer than their own historical median gap.

This is aligned with the project goal because it detects behavioral slowdown relative to each user's normal buying pattern.

Final definition:

> `early_decay_label = 1` if `next_gap_days >= 2.0 x historical_median_gap_days`, with at least 3 known gaps up to the current order.

The 30-day cap is used for **severity ranking**, not as an automatic churn label.

Rows where the 30-day cap makes the 2x outcome unknowable are marked as censored-uncertain and excluded from supervised modeling.

## Leakage Rules For Modeling

- Use `early_decay_label` as the target.
- Use only rows where `label_eligible == True`.
- Exclude `label_status == 'censored_uncertain'` rows from supervised training and final evaluation.
- Do not use `next_order_id`, `next_order_number`, `next_eval_set`, `next_gap_days`, or any label columns as model features.
- Do not use `user_id` as a model feature.
- Use `decay_severity_score`, `decay_severity_tier`, and `gap_cap_30_flag` for post-model ranking/intervention analysis, not as direct model features unless intentionally building a prioritization layer.
