# Instacart Cleaning and Validation Report

## Scope
- Raw Kaggle files were left unchanged.
- Cleaned outputs were written to `data/processed/instacart`.
- Order-product rows were validated and aggregated to basket-level order summaries for EDA/modeling.
- Calendar dates are not present in this dataset; `relative_day` reconstructs each user's timeline from `days_since_prior_order`.

## Project-Relevant Result
- Users: 206,209.
- Orders: 3,421,083.
- Prior order-product rows: 32,434,489.
- Train order-product rows: 1,384,617.
- Users with 3+ behavior orders: 206,209 (100.00%).
- Users with 5+ behavior orders: 175,072 (84.90%).
- Median observed span: 145.0 days; max observed span: 365.0 days.

## Interpretation for Behavioral Decay Modeling
- Instacart is cleaned and strongly viable for sequence-based behavioral decay modeling.
- It supports gap acceleration, basket shrinkage, reorder-ratio decline, department narrowing, and routine breakdown features.
- Use `relative_day` and `order_number` for time-aware splits because real calendar dates are unavailable.
- Test-set orders intentionally have no basket detail; use prior/train orders for feature EDA and sequence label design.

## Validation Summary
- Eval set counts: {'prior': 3214874, 'train': 131209, 'test': 75000}.
- Sequence validation: {'users': 206209, 'orders_per_user_min': 4, 'orders_per_user_median': 10.0, 'orders_per_user_max': 100, 'users_with_non_contiguous_order_numbers': 0, 'duplicate_order_ids': 0, 'duplicate_user_order_numbers': 0, 'first_orders_with_nonnull_gap': 0, 'non_first_orders_with_null_gap': 0, 'gap_days_outside_0_30': 0, 'order_dow_outside_0_6': 0, 'order_hour_outside_0_23': 0, 'max_reconstructed_user_span_days': 365.0, 'median_reconstructed_user_span_days': 151.0}.
- Catalog validation: {'duplicate_aisle_ids': 0, 'duplicate_department_ids': 0, 'duplicate_product_ids': 0, 'products_without_aisle': 0, 'products_without_department': 0}.
- Basket detail by eval set: {'prior': {'orders': 3214874, 'orders_with_basket_detail': 3214874, 'missing_basket_detail': 0}, 'test': {'orders': 75000, 'orders_with_basket_detail': 0, 'missing_basket_detail': 75000}, 'train': {'orders': 131209, 'orders_with_basket_detail': 131209, 'missing_basket_detail': 0}}.
- Order-products validation: {'prior': {'rows': 32434489, 'missing_values_total': 0, 'duplicate_order_product_rows': 0, 'duplicate_cart_positions': 0, 'invalid_reordered_values': 0, 'invalid_add_to_cart_order': 0, 'order_ids_not_in_orders_table': 0, 'product_ids_not_in_catalog': 0}, 'train': {'rows': 1384617, 'missing_values_total': 0, 'duplicate_order_product_rows': 0, 'duplicate_cart_positions': 0, 'invalid_reordered_values': 0, 'invalid_add_to_cart_order': 0, 'order_ids_not_in_orders_table': 0, 'product_ids_not_in_catalog': 0}}.

## Cleaned Files
- `aisles_clean.csv`
- `departments_clean.csv`
- `product_catalog_clean.csv`
- `orders_clean.csv`
- `order_baskets_clean.csv`
- `user_order_behavior_base.csv`
- `user_behavior_summary.csv`
