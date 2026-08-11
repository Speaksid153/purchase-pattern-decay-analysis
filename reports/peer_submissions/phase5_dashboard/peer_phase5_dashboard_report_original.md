======================================================================
RISK SCORE DISTRIBUTION (full eligible population)
======================================================================
count    2.593914e+06
mean     4.648309e-01
std      1.841225e-01
min      1.379461e-06
25%      4.134214e-01
50%      5.140821e-01
75%      5.813873e-01
max      9.587981e-01
Name: risk_score_xgboost, dtype: float64

Percentile cutoffs (for risk tier discussion):
  50th percentile: 0.5141
  70th percentile: 0.5674
  80th percentile: 0.5970
  90th percentile: 0.6377
  95th percentile: 0.6700

======================================================================
TOP RISK DRIVER DISTRIBUTION (full population)
======================================================================
                                  count   pct
top_risk_driver                              
base_avg_days_between_orders    1162218  44.8
base_avg_reorder_ratio_to_date   644793  24.9
base_avg_basket_size_to_date     203306   7.8
base_user_tenure_days            199793   7.7
base_total_orders_to_date        179768   6.9
base_order_hour                  128423   5.0
base_order_dow                    75613   2.9

======================================================================
HIGH-RISK CUSTOMER PROFILE (top 5% by latest snapshot)
======================================================================
Top 5% risk threshold: 0.6814
Number of high-risk customers (latest snapshot): 9,109

Top risk drivers among high-risk customers specifically:
top_risk_driver
base_avg_days_between_orders      51.0
base_avg_reorder_ratio_to_date    39.8
base_avg_basket_size_to_date       5.5
base_user_tenure_days              1.5
base_total_orders_to_date          1.0
base_order_hour                    0.9
base_order_dow                     0.3
Name: proportion, dtype: float64

======================================================================
SCOPE / COVERAGE CHECK
======================================================================
Total Instacart users: 206,209
Eligible users (in dashboard): 182,171 (88.3%)
Excluded users (insufficient history): 24,038 (11.7%)

- Median risk score is 0.51 with a fairly tight middle-50% spread (0.41-0.58) — the model doesn't cleanly separate customers into confident low/high buckets, consistent with its low precision (~0.22-0.23).
- Percentile-based tier thresholds (data-grounded, for discussion with Sid): Low < 0.51, Medium 0.51-0.64, High > 0.64 (or > 0.67 for a stricter top-5% "High" definition).
- Across the full population, avg_days_between_orders (44.8%) and avg_reorder_ratio (24.9%) are the dominant top risk drivers — matches Phase 4 feature importance closely.
- Among the top 5% highest-risk customers specifically (9,109 users), these two drivers become even more dominant (51.0% and 39.8% respectively) — when the model is most confident someone is at risk, it's almost always due to gap length or reorder decline, rarely basket size, tenure, or timing patterns.
- Dashboard covers 182,171 of 206,209 total Instacart users (88.3%) — the excluded 11.7% have fewer than 3 historical orders, so the churn label is structurally undefined for them, not a lookup limitation.