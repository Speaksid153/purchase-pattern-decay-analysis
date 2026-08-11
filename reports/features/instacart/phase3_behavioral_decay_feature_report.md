# Phase 3 Behavioral Decay Feature Report - Instacart

## Objective

The goal of this phase was to convert the Phase 2 churn label into a usable modeling dataset by creating **leading behavioral decay signals**. These features are designed to catch users whose buying behavior is weakening before they fully stop purchasing.

This phase focuses on behavioral decay, not generic churn scoring. The main question is:

> Can we detect early warning signs such as slower purchasing rhythm, weaker basket behavior, declining reorder habits, or narrowing category engagement before the next long purchase gap occurs?

## Dataset Used

The feature build uses the cleaned Instacart user-order behavior table and the Phase 2 decay labels.

- Behavior rows processed: **3,346,083**
- Label rows available: **3,346,083**
- Label-eligible rows used for validation: **2,489,335**
- Feature columns created: **38**
- Model-input feature output: `data/processed/instacart/features/instacart_leading_features_model_input.pkl`
- Target output: `data/processed/instacart/features/instacart_leading_feature_targets.pkl`
- Feature inspection sample: `data/processed/instacart/features/instacart_leading_features_model_input_sample.csv`
- Target inspection sample: `data/processed/instacart/features/instacart_leading_feature_targets_sample.csv`

The full model-input table is saved as a pickle file instead of a full CSV because it is large. A 100k-row CSV sample is saved separately for manual inspection. The target is saved separately to reduce accidental target leakage.

## Leakage Control

Feature generation only uses information available at or before the current order snapshot.

Allowed feature inputs:

- Current order behavior
- Historical order gaps
- Historical basket size
- Historical reorder ratio
- Historical aisle/department diversity
- Historical order day/hour behavior
- User history depth

Not allowed as model features:

- `next_gap_days`
- `next_order_id`
- `next_eval_set`
- `early_decay_label`
- `label_eligible`
- `label_status`
- Future severity/ranking columns

The future label is used only after feature creation to validate whether each feature separates early-decay vs retained rows.

## Feature Groups Built

### 1. Purchase Cadence Decay

Purpose: detect whether the current purchase gap is unusually long for that user.

Key features:

- `current_gap_ratio_to_historical_median`
- `current_gap_gt_1_5x_historical_median`
- `current_gap_gt_2x_historical_median`
- `gap_slope_last3`
- `purchase_frequency_slope_last3`

Interpretation:

- Higher gap ratio = user is buying more slowly than normal.
- Positive gap slope = gaps are widening.
- Negative purchase-frequency slope = purchase frequency is declining.

### 2. Inter-Purchase Gap Acceleration

Purpose: compare the latest gap against the user's earlier purchase rhythm.

Key features:

- `latest_gap_ratio_to_prior_avg`
- `latest_gap_ratio_to_previous_gap`
- `gap_acceleration_1_5x_flag`

Interpretation:

- A ratio above `1.5` means the latest gap is at least 50% longer than the user's normal/previous pattern.

### 3. Basket Size Trend

Purpose: detect shrinking purchase commitment.

Instacart does not contain prices, so order value cannot be calculated. Basket size is used instead.

Key features:

- `item_count_recent3_ratio_to_prior`
- `basket_size_decay_flag`

Interpretation:

- Lower ratios suggest recent baskets are smaller than the user's historical norm.
- `unique_product_count` is intentionally not used as a separate trend feature because it duplicates `item_count` in this Instacart data.

### 4. Reorder Behavior Decay

Purpose: detect weakening repeat-purchase habits.

Key features:

- `reorder_ratio_recent3_ratio_to_prior`
- `reorder_ratio_recent3_delta_from_prior`
- `reorder_ratio_slope_last3`
- `reorder_behavior_decay_flag`

Interpretation:

- Lower reorder ratio can mean the user's routine items are becoming less consistent.

### 5. Category Diversity Narrowing

Purpose: detect whether the user's baskets are becoming narrower.

Key features:

- `distinct_department_count_recent3_ratio_to_prior`
- `distinct_aisle_count_recent3_ratio_to_prior`
- `category_diversity_narrowing_flag`

Interpretation:

- Lower ratios suggest the user is buying from fewer departments/aisles than before.

### 6. Time-of-Order Consistency Decay

Purpose: detect whether users are drifting away from their usual ordering pattern.

Key features:

- `hour_distance_from_prior_pattern`
- `dow_distance_from_prior_pattern`
- `time_consistency_decay_flag`

Interpretation:

- Larger distance means the user is ordering at less typical times compared with their own history.

### 7. Reliability and Ranking Features

Purpose: support warning prioritization and interpretability.

Key features:

- `behavior_orders_to_date`
- `known_gap_count_feature`
- `trend_history_available`
- `history_reliability_score`

Interpretation:

- Signals from customers with more order history are more trustworthy.
- These features are more useful for ranking/interpretability than direct prediction.

## Feature Validation Results

Each feature was validated by comparing its distribution across retained vs early-decay rows.

Baseline early-decay rate among eligible rows: **17.87%**

| Feature | Risk Direction | Risk-Decile Decay Rate | Lift | AUC |
|---|---:|---:|---:|---:|
| `current_gap_ratio_to_historical_median` | high | 34.04% | 1.90 | 0.575 |
| `latest_gap_ratio_to_prior_avg` | high | 31.78% | 1.78 | 0.533 |
| `gap_slope_last3` | high | 24.63% | 1.38 | 0.524 |
| `purchase_frequency_slope_last3` | low | 21.34% | 1.21 | 0.519 |
| `item_count_recent3_ratio_to_prior` | low | 19.64% | 1.10 | 0.511 |
| `distinct_aisle_count_recent3_ratio_to_prior` | low | 19.60% | 1.10 | 0.509 |
| `distinct_department_count_recent3_ratio_to_prior` | low | 19.49% | 1.09 | 0.508 |
| `latest_gap_ratio_to_previous_gap` | high | 23.11% | 1.30 | 0.508 |
| `dow_distance_from_prior_pattern` | high | 17.97% | 1.01 | 0.505 |
| `hour_distance_from_prior_pattern` | high | 18.14% | 1.01 | 0.501 |
| `reorder_ratio_slope_last3` | low | 19.06% | 1.07 | 0.495 |
| `reorder_ratio_recent3_delta_from_prior` | low | 17.59% | 0.98 | 0.489 |
| `history_reliability_score` | high | 17.28% | 0.97 | 0.485 |

## Interpretation

The strongest standalone signal is clearly **purchase cadence decay**.

The top-risk decile of `current_gap_ratio_to_historical_median` has an early-decay rate of **34.04%**, compared with the baseline rate of **17.87%**. That is a **1.90x lift**, meaning users whose current gap is unusually long are almost twice as likely to enter early decay.

The second strongest signal is `latest_gap_ratio_to_prior_avg`, with a **31.78%** early-decay rate in its riskiest decile and **1.78x lift**.

Basket size, category diversity, reorder behavior, and time-consistency features are much weaker as standalone predictors. Most of them sit close to AUC `0.50`, meaning they do not strongly separate early-decay and retained users by themselves.

This does not mean those features are useless. It means they should not be oversold as individual churn indicators. Their value should be tested inside a multivariate model, where combinations such as:

- widening gap + shrinking basket
- widening gap + category narrowing
- widening gap + weaker reorder behavior
- short history + capped gap warning

may provide stronger business insight than any single feature alone.

## Important Limitation

The feature validation is partly shaped by the Phase 2 label definition. Since the label itself is based on future purchase-gap expansion, gap-related features are naturally expected to perform best.

This is not a bug, but it means the project should be careful with the claim:

> We are not proving that every behavioral feature independently predicts churn.

The stronger claim is:

> Purchase cadence decay is the clearest early warning signal, while basket, category, reorder, and timing features can help explain the type and seriousness of decay once a user is flagged.

That is more defensible and more realistic.

## Actionable Business Interpretation

The feature set supports practical intervention logic:

| Warning Pattern | Possible Interpretation | Possible Action |
|---|---|---|
| Gap ratio is high | User is ordering slower than normal | Send reminder or replenishment prompt |
| Gap ratio high + basket shrinking | User is reducing purchase commitment | Offer personalized bundle or basket-building promotion |
| Gap ratio high + category narrowing | User is using the platform for fewer needs | Recommend products from previously used categories |
| Gap ratio high + reorder ratio falling | Routine purchasing habit is weakening | Promote reorder shortcuts or saved basket |
| Gap warning with strong history reliability | Higher-confidence warning | Prioritize for intervention |
| Gap warning with low history reliability | Noisy warning | Treat as lower-confidence watchlist case |

## Modeling Recommendation

For the next phase, use these features in two tracks:

1. **Baseline model**
   - Use simple recency/frequency/basket features.
   - Purpose: show what a standard churn model captures.

2. **Leading-indicator model**
   - Add cadence decay, gap acceleration, basket trend, reorder decay, category narrowing, time consistency, and reliability features.
   - Purpose: show whether behavioral decay features improve early warning performance and interpretability.

Recommended first models:

- Logistic Regression for interpretable baseline
- Random Forest or Gradient Boosting for nonlinear interactions
- SHAP or permutation importance for explanation

Primary evaluation metrics:

- ROC AUC
- Precision/recall at top-risk deciles
- Lift in top 5% and top 10%
- Feature importance/explanation quality

## Final Phase 3 Conclusion

Phase 3 successfully created a leakage-safe behavioral feature set for early churn/decay modeling. The model-input feature file is saved separately from the target file, so the next phase can train without accidentally using label columns as predictors.

The strongest current evidence supports a narrower and defensible version of the project's thesis: **purchase rhythm decay is the clearest early warning signal in this dataset.**

However, the results also show that not every behavioral signal is equally useful. Cadence and gap acceleration are the main predictive signals. Basket, reorder, category, and timing features are better positioned as supporting explanation/ranking features unless the modeling phase proves that they add meaningful incremental lift.

This is a stronger project story than pretending every feature worked equally well.
