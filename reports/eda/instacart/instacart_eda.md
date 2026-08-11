# Instacart EDA Report

## Executive Takeaway
Instacart is a strong primary dataset for early behavioral decay modeling. It has repeated user order sequences, reconstructed relative timelines, basket size, reorder behavior, and product/category structure.

## Scope
- Orders: 3,421,083.
- Users: 206,209.
- Behavior orders with basket detail: 3,346,083.
- Test orders without basket detail: 75,000.
- Eval sets: {'prior': 3214874, 'train': 131209, 'test': 75000}.

## Sequence Depth
- Median orders per user: 10.0.
- Median reconstructed span: 145.0 days.
- Users with 5+ orders: 182,223.
- Users with 10+ orders: 110,728.

## Behavioral Signal Distributions
- Median gap between orders: 7.0 days.
- Median basket size: 8.0 items.
- Median reorder ratio: 0.67.
- Median distinct departments per basket: 4.0.

## Future Inactivity Label Feasibility
- Valid sequence rows for next-gap modeling: 2,724,527.
- Rows followed by a future 30-day gap: 250,804 (9.21%).
- Rows followed by a future gap at least 2x prior average: 319,500 (11.73%).

## Early Indicator Readout
| Feature | Normal median | Future 30d gap median |
|---|---:|---:|
| days_since_prior_order | 7.000 | 18.000 |
| gap_ratio_to_prior_avg | 0.857 | 1.034 |
| item_count | 8.000 | 8.000 |
| basket_size_ratio_to_prior_avg | 0.955 | 0.931 |
| reorder_ratio | 0.733 | 0.556 |
| reorder_ratio_delta_from_prior_avg | 0.183 | 0.211 |
| distinct_department_count | 4.000 | 4.000 |
| department_count_ratio_to_prior_avg | 1.000 | 0.980 |

## Segment Lift Checks
| Segment | Threshold | Future gap rate | Lift vs baseline | Rows |
|---|---:|---:|---:|---:|
| top_decile_gap_ratio | 2.061 | 13.65% | 1.48x | 272,532 |
| bottom_decile_basket_ratio | 0.410 | 10.82% | 1.18x | 272,534 |
| bottom_decile_reorder_delta | -0.151 | 9.08% | 0.99x | 272,453 |
| bottom_decile_department_ratio | 0.500 | 11.14% | 1.21x | 279,534 |

## Actionable Intervention Mapping
- High gap acceleration: replenishment reminder or timing-based reactivation.
- Basket size contraction: personalized bundle, minimum-cart incentive, or basket-builder recommendation.
- Reorder ratio decline: one-click reorder of usual products or staple recovery prompt.
- Department/category narrowing: category-specific offer or recommendation to restore routine breadth.
- Routine timing irregularity: habit-restoration reminder keyed to the user's normal reorder interval.

## Recommended Use
- Use Instacart as the main dataset for the behavioral decay project.
- Build labels around future gap expansion, not generic calendar churn.
- Compare leading decay features against traditional RFM-style baselines using the same model family.

## Plots
- `plots/orders_per_user_distribution.png`
- `plots/user_span_distribution.png`
- `plots/gap_distribution.png`
- `plots/basket_size_distribution.png`
- `plots/reorder_ratio_distribution.png`
- `plots/gap_ratio_distribution.png`
- `plots/gap_ratio_by_future_gap.png`
- `plots/basket_ratio_by_future_gap.png`
- `plots/reorder_delta_by_future_gap.png`
- `plots/orders_by_dow.png`
- `plots/orders_by_hour.png`
- `plots/top_departments.png`
