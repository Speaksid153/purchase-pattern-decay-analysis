from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "instacart"
OUT = ROOT / "data" / "processed" / "instacart"
REPORT_DIR = ROOT / "reports" / "data_validation"


ORDER_DTYPES = {
    "order_id": "uint32",
    "user_id": "uint32",
    "eval_set": "category",
    "order_number": "uint16",
    "order_dow": "uint8",
    "order_hour_of_day": "uint8",
    "days_since_prior_order": "float32",
}

ORDER_PRODUCT_DTYPES = {
    "order_id": "uint32",
    "product_id": "uint32",
    "add_to_cart_order": "uint16",
    "reordered": "uint8",
}


def ensure_dirs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def read_csv(name: str, **kwargs) -> pd.DataFrame:
    df = pd.read_csv(RAW / name, **kwargs)
    df.columns = [c.strip().replace("\ufeff", "") for c in df.columns]
    return df


def clean_text(series: pd.Series) -> pd.Series:
    out = series.astype("string").str.strip().str.lower()
    return out.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})


def missing_summary(df: pd.DataFrame) -> dict[str, int]:
    return {col: int(df[col].isna().sum()) for col in df.columns if int(df[col].isna().sum())}


def duplicate_count(df: pd.DataFrame, cols: list[str]) -> int:
    return int(df.duplicated(cols).sum())


def clean_catalog() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    aisles = read_csv("aisles.csv")
    departments = read_csv("departments.csv")
    products = read_csv("products.csv")

    aisles["aisle"] = clean_text(aisles["aisle"])
    departments["department"] = clean_text(departments["department"])
    products["product_name"] = products["product_name"].astype("string").str.strip()

    catalog = (
        products.merge(aisles, on="aisle_id", how="left")
        .merge(departments, on="department_id", how="left")
        .sort_values("product_id")
    )
    return aisles, departments, catalog


def aggregate_order_products(
    path: Path,
    eval_set: str,
    valid_order_ids: set[int],
    product_lookup: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    op = pd.read_csv(path, dtype=ORDER_PRODUCT_DTYPES)
    validation = {
        "rows": int(len(op)),
        "missing_values_total": int(op.isna().sum().sum()),
        "duplicate_order_product_rows": duplicate_count(op, ["order_id", "product_id"]),
        "duplicate_cart_positions": duplicate_count(op, ["order_id", "add_to_cart_order"]),
        "invalid_reordered_values": int((~op["reordered"].isin([0, 1])).sum()),
        "invalid_add_to_cart_order": int((op["add_to_cart_order"] < 1).sum()),
        "order_ids_not_in_orders_table": int((~op["order_id"].isin(valid_order_ids)).sum()),
    }

    product_ids = set(product_lookup["product_id"].astype(int))
    validation["product_ids_not_in_catalog"] = int((~op["product_id"].isin(product_ids)).sum())

    product_map = product_lookup[["product_id", "aisle_id", "department_id"]].astype(
        {"product_id": "uint32", "aisle_id": "uint16", "department_id": "uint8"}
    )
    op = op.merge(product_map, on="product_id", how="left")

    basket = (
        op.groupby("order_id", as_index=False)
        .agg(
            item_count=("product_id", "count"),
            unique_product_count=("product_id", "nunique"),
            reorder_item_count=("reordered", "sum"),
            max_add_to_cart_order=("add_to_cart_order", "max"),
            distinct_aisle_count=("aisle_id", "nunique"),
            distinct_department_count=("department_id", "nunique"),
        )
        .sort_values("order_id")
    )
    basket["reorder_ratio"] = basket["reorder_item_count"] / basket["item_count"]
    basket["eval_set"] = eval_set
    return basket, validation


def add_behavior_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["user_id", "order_number"]).copy()
    df["relative_day"] = df.groupby("user_id")["days_since_prior_order"].transform(
        lambda s: s.fillna(0).cumsum()
    )
    df["is_first_order"] = df["order_number"].eq(1)
    df["is_last_observed_order"] = df.groupby("user_id")["order_number"].transform("max").eq(df["order_number"])
    df["next_days_until_order"] = df.groupby("user_id")["days_since_prior_order"].shift(-1)
    df["has_next_order_observed"] = df["next_days_until_order"].notna()

    # Historical, leakage-safe reference values available before the current order.
    for col, out_col in [
        ("days_since_prior_order", "prior_avg_gap_days"),
        ("item_count", "prior_avg_item_count"),
        ("reorder_ratio", "prior_avg_reorder_ratio"),
        ("distinct_department_count", "prior_avg_distinct_department_count"),
    ]:
        valid = df[col].notna()
        cumulative = df[col].fillna(0).groupby(df["user_id"]).cumsum()
        valid_count = valid.astype("int32").groupby(df["user_id"]).cumsum()
        prior_sum = cumulative - df[col].fillna(0)
        prior_count = valid_count - valid.astype("int32")
        prior_value = prior_sum / prior_count.replace(0, np.nan)
        df[out_col] = prior_value.replace([np.inf, -np.inf], np.nan)

    df["gap_ratio_to_prior_avg"] = df["days_since_prior_order"] / df["prior_avg_gap_days"]
    df["basket_size_ratio_to_prior_avg"] = df["item_count"] / df["prior_avg_item_count"]
    df["reorder_ratio_delta_from_prior_avg"] = df["reorder_ratio"] - df["prior_avg_reorder_ratio"]
    df["department_count_ratio_to_prior_avg"] = (
        df["distinct_department_count"] / df["prior_avg_distinct_department_count"]
    )

    df["candidate_future_gap_30d"] = df["next_days_until_order"] >= 30
    df["candidate_future_gap_2x_prior_avg"] = (
        df["prior_avg_gap_days"].notna()
        & df["prior_avg_gap_days"].gt(0)
        & df["next_days_until_order"].notna()
        & (df["next_days_until_order"] >= 2 * df["prior_avg_gap_days"])
    )
    return df.replace([np.inf, -np.inf], np.nan)


def main() -> None:
    ensure_dirs()

    aisles, departments, catalog = clean_catalog()
    orders = read_csv("orders.csv", dtype=ORDER_DTYPES)
    orders["eval_set"] = orders["eval_set"].astype("string").str.strip().str.lower()
    orders = orders.sort_values(["user_id", "order_number", "order_id"])

    raw_counts = {
        "orders": len(orders),
        "aisles": len(aisles),
        "departments": len(departments),
        "products": len(catalog),
    }

    valid_orders = set(orders["order_id"].astype(int))
    prior_basket, prior_validation = aggregate_order_products(
        RAW / "order_products__prior.csv",
        "prior",
        valid_orders,
        catalog,
    )
    train_basket, train_validation = aggregate_order_products(
        RAW / "order_products__train.csv",
        "train",
        valid_orders,
        catalog,
    )
    basket_summary = pd.concat([prior_basket, train_basket], ignore_index=True).sort_values("order_id")

    orders_clean = orders.copy()
    orders_clean["days_since_prior_order_filled"] = orders_clean["days_since_prior_order"].fillna(0)
    orders_clean["relative_day"] = orders_clean.groupby("user_id")[
        "days_since_prior_order_filled"
    ].cumsum()
    orders_clean["is_first_order"] = orders_clean["order_number"].eq(1)

    order_behavior = orders_clean.merge(basket_summary.drop(columns=["eval_set"]), on="order_id", how="left")
    order_behavior["has_basket_detail"] = order_behavior["item_count"].notna()
    user_order_behavior = add_behavior_columns(
        order_behavior[order_behavior["has_basket_detail"]].copy()
    )

    user_summary = (
        user_order_behavior.groupby("user_id", as_index=False)
        .agg(
            observed_orders_with_baskets=("order_id", "nunique"),
            first_relative_day=("relative_day", "min"),
            last_relative_day=("relative_day", "max"),
            avg_gap_days=("days_since_prior_order", "mean"),
            median_gap_days=("days_since_prior_order", "median"),
            avg_item_count=("item_count", "mean"),
            avg_reorder_ratio=("reorder_ratio", "mean"),
            avg_distinct_department_count=("distinct_department_count", "mean"),
            max_item_count=("item_count", "max"),
            final_observed_eval_set=("eval_set", lambda s: s.iloc[-1]),
        )
    )
    user_summary["observed_span_days"] = user_summary["last_relative_day"] - user_summary["first_relative_day"]
    user_summary["supports_3plus_behavior_orders"] = user_summary["observed_orders_with_baskets"] >= 3
    user_summary["supports_5plus_behavior_orders"] = user_summary["observed_orders_with_baskets"] >= 5

    # Sequence validations.
    order_sequence = orders.groupby("user_id")["order_number"]
    order_counts_by_user = order_sequence.count()
    span_by_user = orders_clean.groupby("user_id")["relative_day"].max()
    seq_validation = {
        "users": int(orders["user_id"].nunique()),
        "orders_per_user_min": int(order_counts_by_user.min()),
        "orders_per_user_median": float(order_counts_by_user.median()),
        "orders_per_user_max": int(order_counts_by_user.max()),
        "users_with_non_contiguous_order_numbers": int(
            orders.groupby("user_id")["order_number"].apply(lambda s: sorted(s.tolist()) != list(range(1, len(s) + 1))).sum()
        ),
        "duplicate_order_ids": duplicate_count(orders, ["order_id"]),
        "duplicate_user_order_numbers": duplicate_count(orders, ["user_id", "order_number"]),
        "first_orders_with_nonnull_gap": int(
            orders.loc[orders["order_number"].eq(1), "days_since_prior_order"].notna().sum()
        ),
        "non_first_orders_with_null_gap": int(
            orders.loc[~orders["order_number"].eq(1), "days_since_prior_order"].isna().sum()
        ),
        "gap_days_outside_0_30": int(
            orders["days_since_prior_order"].dropna().pipe(lambda s: ((s < 0) | (s > 30)).sum())
        ),
        "order_dow_outside_0_6": int(((orders["order_dow"] < 0) | (orders["order_dow"] > 6)).sum()),
        "order_hour_outside_0_23": int(
            ((orders["order_hour_of_day"] < 0) | (orders["order_hour_of_day"] > 23)).sum()
        ),
        "max_reconstructed_user_span_days": float(span_by_user.max()),
        "median_reconstructed_user_span_days": float(span_by_user.median()),
    }

    basket_missing_by_eval_set = (
        order_behavior.groupby("eval_set")["has_basket_detail"]
        .agg(["count", "sum"])
        .rename(columns={"count": "orders", "sum": "orders_with_basket_detail"})
    )
    basket_missing_by_eval_set["missing_basket_detail"] = (
        basket_missing_by_eval_set["orders"] - basket_missing_by_eval_set["orders_with_basket_detail"]
    )

    validation: dict[str, object] = {
        "raw_counts": raw_counts
        | {
            "order_products_prior": prior_validation["rows"],
            "order_products_train": train_validation["rows"],
        },
        "clean_counts": {
            "orders_clean": len(orders_clean),
            "basket_summary": len(basket_summary),
            "user_order_behavior_base": len(user_order_behavior),
            "user_behavior_summary": len(user_summary),
        },
        "eval_set_counts": orders["eval_set"].value_counts().to_dict(),
        "sequence_validation": seq_validation,
        "catalog_validation": {
            "duplicate_aisle_ids": duplicate_count(aisles, ["aisle_id"]),
            "duplicate_department_ids": duplicate_count(departments, ["department_id"]),
            "duplicate_product_ids": duplicate_count(catalog, ["product_id"]),
            "products_without_aisle": int(catalog["aisle"].isna().sum()),
            "products_without_department": int(catalog["department"].isna().sum()),
        },
        "order_products_validation": {
            "prior": prior_validation,
            "train": train_validation,
        },
        "missing_values": {
            "orders": missing_summary(orders),
            "catalog": missing_summary(catalog),
            "basket_summary": missing_summary(basket_summary),
        },
        "basket_detail_by_eval_set": basket_missing_by_eval_set.astype(int).to_dict(orient="index"),
        "project_viability": {
            "users": int(user_summary["user_id"].nunique()),
            "users_with_3plus_behavior_orders": int(user_summary["supports_3plus_behavior_orders"].sum()),
            "users_with_5plus_behavior_orders": int(user_summary["supports_5plus_behavior_orders"].sum()),
            "share_with_3plus_behavior_orders": float(user_summary["supports_3plus_behavior_orders"].mean()),
            "share_with_5plus_behavior_orders": float(user_summary["supports_5plus_behavior_orders"].mean()),
            "median_orders_with_baskets_per_user": float(user_summary["observed_orders_with_baskets"].median()),
            "median_observed_span_days": float(user_summary["observed_span_days"].median()),
            "max_observed_span_days": float(user_summary["observed_span_days"].max()),
        },
    }

    aisles.to_csv(OUT / "aisles_clean.csv", index=False)
    departments.to_csv(OUT / "departments_clean.csv", index=False)
    catalog.to_csv(OUT / "product_catalog_clean.csv", index=False)
    orders_clean.to_csv(OUT / "orders_clean.csv", index=False)
    basket_summary.to_csv(OUT / "order_baskets_clean.csv", index=False)
    user_order_behavior.to_csv(OUT / "user_order_behavior_base.csv", index=False)
    user_summary.to_csv(OUT / "user_behavior_summary.csv", index=False)

    with (REPORT_DIR / "instacart_validation.json").open("w", encoding="utf-8") as f:
        json.dump(validation, f, indent=2, default=str)

    lines = [
        "# Instacart Cleaning and Validation Report",
        "",
        "## Scope",
        "- Raw Kaggle files were left unchanged.",
        "- Cleaned outputs were written to `data/processed/instacart`.",
        "- Order-product rows were validated and aggregated to basket-level order summaries for EDA/modeling.",
        "- Calendar dates are not present in this dataset; `relative_day` reconstructs each user's timeline from `days_since_prior_order`.",
        "",
        "## Project-Relevant Result",
        f"- Users: {validation['project_viability']['users']:,}.",
        f"- Orders: {validation['raw_counts']['orders']:,}.",
        f"- Prior order-product rows: {validation['raw_counts']['order_products_prior']:,}.",
        f"- Train order-product rows: {validation['raw_counts']['order_products_train']:,}.",
        (
            f"- Users with 3+ behavior orders: "
            f"{validation['project_viability']['users_with_3plus_behavior_orders']:,} "
            f"({validation['project_viability']['share_with_3plus_behavior_orders']:.2%})."
        ),
        (
            f"- Users with 5+ behavior orders: "
            f"{validation['project_viability']['users_with_5plus_behavior_orders']:,} "
            f"({validation['project_viability']['share_with_5plus_behavior_orders']:.2%})."
        ),
        (
            f"- Median observed span: {validation['project_viability']['median_observed_span_days']:.1f} days; "
            f"max observed span: {validation['project_viability']['max_observed_span_days']:.1f} days."
        ),
        "",
        "## Interpretation for Behavioral Decay Modeling",
        "- Instacart is cleaned and strongly viable for sequence-based behavioral decay modeling.",
        "- It supports gap acceleration, basket shrinkage, reorder-ratio decline, department narrowing, and routine breakdown features.",
        "- Use `relative_day` and `order_number` for time-aware splits because real calendar dates are unavailable.",
        "- Test-set orders intentionally have no basket detail; use prior/train orders for feature EDA and sequence label design.",
        "",
        "## Validation Summary",
        f"- Eval set counts: {validation['eval_set_counts']}.",
        f"- Sequence validation: {validation['sequence_validation']}.",
        f"- Catalog validation: {validation['catalog_validation']}.",
        f"- Basket detail by eval set: {validation['basket_detail_by_eval_set']}.",
        f"- Order-products validation: {validation['order_products_validation']}.",
        "",
        "## Cleaned Files",
        "- `aisles_clean.csv`",
        "- `departments_clean.csv`",
        "- `product_catalog_clean.csv`",
        "- `orders_clean.csv`",
        "- `order_baskets_clean.csv`",
        "- `user_order_behavior_base.csv`",
        "- `user_behavior_summary.csv`",
    ]
    (REPORT_DIR / "instacart_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(validation["project_viability"], indent=2))


if __name__ == "__main__":
    main()
