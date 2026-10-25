#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KAN-7 - Product, Review, Inventory, Promotion, Order_Item_Promotion.
Uses the cleaning logic from the full cleaning script; writes only the CSVs assigned to this group.

Usage:
    python clean_ecommerce_data.py --input student_data.zip --output cleaned_output

Requirements:
    pip install pandas

Design choices:
- Does NOT filter orders by date. All valid source orders are preserved.
- Does NOT drop rows just because they look unusual. Potential problems are written
  to audit_report.txt / audit_*.csv for review.
- Trims text fields and normalizes date/numeric/boolean fields where appropriate.
- Creates a stable order_item_id based on the original order_items.csv row order.
- Maps each return to order_item_id by (order_id, product_id). If the same pair
  occurs more than once, returns are assigned in source order to distinct matching
  items when possible. Ambiguous mappings are recorded in the audit report.
"""

import argparse
import json
import re
import zipfile
from pathlib import Path

import pandas as pd


def read_csv_from_zip(zf, filename):
    matches = [n for n in zf.namelist() if n.lower().endswith("/" + filename.lower())]
    if not matches:
        matches = [n for n in zf.namelist() if Path(n).name.lower() == filename.lower()]
    if not matches:
        raise FileNotFoundError(f"Could not find {filename} inside the input ZIP.")
    return pd.read_csv(zf.open(matches[0]), low_memory=False)


def clean_text_columns(df):
    df = df.copy()
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].map(
            lambda x: x.strip() if isinstance(x, str) else x
        )
        df[col] = df[col].replace("", pd.NA)
    return df


def parse_dates(df, columns, audit, table_name):
    df = df.copy()
    for col in columns:
        if col in df.columns:
            original_nonempty = df[col].notna() & (df[col].astype(str).str.strip() != "")
            parsed = pd.to_datetime(df[col], errors="coerce")
            invalid = original_nonempty & parsed.isna()
            if invalid.any():
                audit.append(
                    f"{table_name}.{col}: {int(invalid.sum())} non-empty value(s) could not be parsed as dates."
                )
            df[col] = parsed.dt.strftime("%Y-%m-%d")
            df.loc[parsed.isna(), col] = pd.NA
    return df


def to_numeric(df, columns, audit, table_name, integer=False):
    df = df.copy()
    for col in columns:
        if col not in df.columns:
            continue
        before = df[col].notna() & (df[col].astype(str).str.strip() != "")
        parsed = pd.to_numeric(df[col], errors="coerce")
        invalid = before & parsed.isna()
        if invalid.any():
            audit.append(
                f"{table_name}.{col}: {int(invalid.sum())} non-empty value(s) could not be parsed as numbers."
            )
        if integer:
            # Preserve nulls if any; use nullable integer dtype.
            df[col] = parsed.round().astype("Int64")
        else:
            df[col] = parsed
    return df


def write_csv(df, outdir, filename):
    df.to_csv(outdir / filename, index=False, encoding="utf-8-sig")


def duplicate_report(df, key_cols, label, outdir, audit):
    existing = [c for c in key_cols if c in df.columns]
    if not existing:
        return
    dup = df[df.duplicated(existing, keep=False)].copy()
    if not dup.empty:
        filename = f"audit_duplicate_{label}.csv"
        dup.to_csv(outdir / filename, index=False, encoding="utf-8-sig")
        audit.append(
            f"{label}: {len(dup)} row(s) have duplicate key {existing}; details: {filename}. "
            "Review before enforcing a primary key."
        )


def main():
    parser = argparse.ArgumentParser(description="KAN-7 - Product, Review, Inventory, Promotion, Order_Item_Promotion. Uses the same cleaning rules as the full script.")
    parser.add_argument("--input", required=True, help="Path to student_data.zip")
    parser.add_argument("--output", default="cleaned_output", help="Output directory")
    args = parser.parse_args()

    input_zip = Path(args.input)
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    audit = []

    with zipfile.ZipFile(input_zip) as zf:
        customers = clean_text_columns(read_csv_from_zip(zf, "customers.csv"))
        geography = clean_text_columns(read_csv_from_zip(zf, "geography.csv"))
        inventory = clean_text_columns(read_csv_from_zip(zf, "inventory.csv"))
        orders_src = clean_text_columns(read_csv_from_zip(zf, "orders_enriched.csv"))
        items_src = clean_text_columns(read_csv_from_zip(zf, "order_items.csv"))
        payments = clean_text_columns(read_csv_from_zip(zf, "payments.csv"))
        products = clean_text_columns(read_csv_from_zip(zf, "products.csv"))
        promotions_src = clean_text_columns(read_csv_from_zip(zf, "promotions.csv"))
        returns_src = clean_text_columns(read_csv_from_zip(zf, "returns.csv"))
        reviews = clean_text_columns(read_csv_from_zip(zf, "reviews.csv"))
        shipments_src = clean_text_columns(read_csv_from_zip(zf, "shipments_realistic.csv"))
        traffic = clean_text_columns(read_csv_from_zip(zf, "web_traffic.csv"))

    # Record raw counts before transformations.
    raw_counts = {
        "customers": len(customers), "geography": len(geography),
        "inventory": len(inventory), "orders": len(orders_src),
        "order_items": len(items_src), "payments": len(payments),
        "products": len(products), "promotions": len(promotions_src),
        "returns": len(returns_src), "reviews": len(reviews),
        "shipments": len(shipments_src), "web_traffic": len(traffic),
    }

    # Parse dates and numeric columns.
    customers = parse_dates(customers, ["signup_date"], audit, "customers")
    geography = geography.drop_duplicates()  # exact duplicate rows only
    inventory = parse_dates(inventory, ["snapshot_date"], audit, "inventory")
    inventory = to_numeric(inventory, [
        "product_id", "stock_on_hand", "units_received", "units_sold",
        "stockout_days", "days_of_supply", "fill_rate", "stockout_flag",
        "overstock_flag", "reorder_flag", "sell_through_rate", "year", "month"
    ], audit, "inventory")
    products = to_numeric(products, ["product_id", "price", "cogs"], audit, "products")
    promotions_src = parse_dates(promotions_src, ["start_date", "end_date"], audit, "promotions")
    promotions_src["promo_id_source"] = promotions_src["promo_id"].astype("string")
    promotions_src["promo_id"] = promotions_src["promo_id_source"].str.extract(r"(\d+)$", expand=False)
    promotions_src = to_numeric(promotions_src, ["promo_id", "discount_value", "stackable_flag", "min_order_value"], audit, "promotions")
    promotions_src["stackable_flag"] = promotions_src["stackable_flag"].map(
        lambda x: pd.NA if pd.isna(x) else bool(int(x))
    )

    orders_src = parse_dates(orders_src, ["order_date"], audit, "orders")
    orders_src = to_numeric(orders_src, ["order_id", "customer_id", "years_experience"], audit, "orders")
    items_src = to_numeric(items_src, ["order_id", "product_id", "quantity", "unit_price", "discount_amount"], audit, "order_items")
    payments = to_numeric(payments, ["order_id", "payment_value", "installments"], audit, "payments")
    returns_src = parse_dates(returns_src, ["return_date"], audit, "returns")
    returns_src = to_numeric(returns_src, ["order_id", "product_id", "return_quantity", "refund_amount"], audit, "returns")
    reviews = parse_dates(reviews, ["review_date"], audit, "reviews")
    reviews = to_numeric(reviews, ["order_id", "product_id", "customer_id", "rating"], audit, "reviews")
    shipments_src = parse_dates(shipments_src, ["ship_date", "delivery_date", "join_date"], audit, "shipments")
    shipments_src = to_numeric(shipments_src, [
        "order_id", "shipping_fee", "shipper_experience_years", "shipper_rating",
        "delivery_success_rate", "average_delivery_time", "shipper_age"
    ], audit, "shipments")
    traffic = parse_dates(traffic, ["date"], audit, "web_traffic")
    traffic = to_numeric(traffic, [
        "sessions", "unique_visitors", "page_views", "bounce_rate",
        "avg_session_duration_sec"
    ], audit, "web_traffic")

    # Keep all orders. Do not silently truncate the date range.
    orders = orders_src[[
        "order_id", "order_date", "order_status", "device_type", "order_source",
        "comment", "customer_id", "sales_employee_id", "zip"
    ]].rename(columns={"zip": "delivery_zip"}).copy()

    # Stable source-row identifier; all item rows are preserved.
    items = items_src.copy()
    items.insert(0, "order_item_id", range(1, len(items) + 1))
    item_key = items[["order_id", "product_id", "order_item_id"]].copy()

    # Promotion bridge: unpivot promo_id and promo_id_2. Preserve only non-empty promo references.
    bridge_parts = []
    promo_lookup = set(promotions_src["promo_id"].dropna().astype("Int64").astype(str))
    for promo_col in ["promo_id", "promo_id_2"]:
        if promo_col not in items_src.columns:
            continue
        part = items[["order_item_id", "order_id", "product_id"]].copy()
        raw = items_src[promo_col].astype("string").str.strip()
        part["promo_id"] = raw.str.extract(r"(\d+)$", expand=False)
        part = part[part["promo_id"].notna()].copy()
        part["promo_id"] = pd.to_numeric(part["promo_id"], errors="coerce").astype("Int64")
        if not part.empty:
            bridge_parts.append(part[["order_item_id", "promo_id"]])
    if bridge_parts:
        bridge = pd.concat(bridge_parts, ignore_index=True).drop_duplicates()
        bridge = bridge[bridge["promo_id"].astype("string").isin(promo_lookup)].copy()
    else:
        bridge = pd.DataFrame(columns=["order_item_id", "promo_id"])

    # Returns: map on order_id + product_id, assigning repeated matching pairs in source order.
    # This resolves the 4 duplicate joins observed in the supplied data without multiplying rows.
    returns = returns_src.copy()
    # Pair occurrence index makes the mapping one-to-one even when the same product
    # appears twice in one order. Source order is used only to disambiguate those cases.
    item_map = item_key.copy()
    item_map["_pair_seq"] = item_map.groupby(["order_id", "product_id"], dropna=False).cumcount()
    returns["_pair_seq"] = returns.groupby(["order_id", "product_id"], dropna=False).cumcount()
    returns = returns.merge(
        item_map[["order_id", "product_id", "order_item_id", "_pair_seq"]],
        on=["order_id", "product_id", "_pair_seq"],
        how="left",
        validate="one_to_one"
    )
    unmatched_returns = returns[returns["order_item_id"].isna()].copy()
    if not unmatched_returns.empty:
        unmatched_returns.drop(columns=["_pair_seq"]).to_csv(
            outdir / "audit_unmatched_returns.csv", index=False, encoding="utf-8-sig"
        )
        audit.append(
            f"returns: {len(unmatched_returns)} row(s) could not be mapped to an order item by (order_id, product_id); "
            "details: audit_unmatched_returns.csv. Do not discard these rows."
        )
    returns = returns.drop(columns=["_pair_seq"])
    returns = returns[[
        "return_id", "order_id", "order_item_id", "return_date",
        "return_reason", "return_quantity", "refund_amount"
    ]]

    # Reviews: retain all rows, normalize review_id to integer where possible to match previous clean schema.
    if "review_id" in reviews.columns:
        reviews["review_id"] = reviews["review_id"].astype("string").str.extract(r"(\d+)$", expand=False)
        reviews["review_id"] = pd.to_numeric(reviews["review_id"], errors="coerce").astype("Int64")

    # Shipments: create one row per source shipment; do not deduplicate by order_id.
    shipments = shipments_src.copy()
    shipments.insert(0, "shipment_id", range(1, len(shipments) + 1))
    shipment_out = shipments[[
        "shipment_id", "order_id", "shipper_id", "ship_date", "delivery_date", "shipping_fee"
    ]].copy()

    # Shipper dimension: one record per shipper_id, retain first non-empty attributes.
    shipper_cols = [
        "shipper_id", "shipper_company", "shipper_name", "shipper_vehicle",
        "shipper_rating", "delivery_success_rate", "shipper_experience_years",
        "join_date", "shipper_phone", "shipper_gender", "shipper_age",
        "shipper_marital_status", "shipper_education"
    ]
    shipper_dim = shipments_src[shipper_cols].copy()
    shipper_dim = shipper_dim.sort_values("shipper_id").drop_duplicates("shipper_id", keep="first")

    # Employee dimension: derive distinct employee attributes from enriched orders.
    employee_cols = [
        "sales_employee_id", "sales_employee_name", "marital_status",
        "education_level", "years_experience"
    ]
    employee = orders_src[employee_cols].copy()
    employee = employee.dropna(subset=["sales_employee_id"])
    # Prefer a row with more populated attributes when an employee has multiple source variants.
    employee["_filled"] = employee[employee_cols[1:]].notna().sum(axis=1)
    employee = employee.sort_values("_filled", ascending=False).drop_duplicates("sales_employee_id", keep="first")
    employee = employee.drop(columns="_filled")

    # Web traffic output schema.
    traffic = traffic.rename(columns={"date": "traffic_date"})

    # Output clean CSVs.
    outputs = {
        "clean_product.csv": products,
        "clean_review.csv": reviews,
        "clean_inventory.csv": inventory,
        "clean_promotion.csv": promotions_src[[
            "promo_id", "promo_name", "promo_type", "discount_value", "start_date",
            "end_date", "applicable_category", "promo_channel", "stackable_flag", "min_order_value"
        ]],
        "clean_order_item_promotion.csv": bridge,
    }

    # Simple, explicit key/relationship audit. These are warnings, not automatic deletions.
    duplicate_report(customers, ["customer_id"], "customers", outdir, audit)
    duplicate_report(products, ["product_id"], "products", outdir, audit)
    duplicate_report(orders, ["order_id"], "orders", outdir, audit)
    duplicate_report(items, ["order_item_id"], "order_items", outdir, audit)
    duplicate_report(returns, ["return_id"], "returns", outdir, audit)
    duplicate_report(reviews, ["review_id"], "reviews", outdir, audit)
    duplicate_report(shipper_dim, ["shipper_id"], "shipper", outdir, audit)
    duplicate_report(employee, ["sales_employee_id"], "employee", outdir, audit)

    order_ids = set(orders["order_id"].dropna())
    item_order_ids = set(items["order_id"].dropna())
    payment_order_ids = set(payments["order_id"].dropna())
    shipment_order_ids = set(shipment_out["order_id"].dropna())
    audit.append(f"Orders preserved: {len(orders)} rows; source had {raw_counts['orders']} rows.")
    audit.append(f"Order items preserved: {len(items)} rows; source had {raw_counts['order_items']} rows.")
    audit.append(f"Payments preserved: {len(payments)} rows; source had {raw_counts['payments']} rows.")
    audit.append(f"Returns preserved: {len(returns)} rows; source had {raw_counts['returns']} rows.")
    audit.append(f"Shipments preserved: {len(shipment_out)} rows; source had {raw_counts['shipments']} rows.")
    audit.append(f"Payment order IDs absent from clean orders: {len(payment_order_ids - order_ids)} distinct order ID(s).")
    audit.append(f"Order-item order IDs absent from clean orders: {len(item_order_ids - order_ids)} distinct order ID(s).")
    audit.append(f"Shipment order IDs absent from clean orders: {len(shipment_order_ids - order_ids)} distinct order ID(s).")

    counts = []
    for filename, df in outputs.items():
        write_csv(df, outdir, filename)
        counts.append({"file": filename, "rows": len(df), "columns": len(df.columns)})

    pd.DataFrame(counts).to_csv(outdir / "audit_row_counts.csv", index=False, encoding="utf-8-sig")
    with open(outdir / "audit_report.txt", "w", encoding="utf-8") as f:
        f.write("E-COMMERCE DATA CLEANING AUDIT\n")
        f.write("=" * 32 + "\n\n")
        f.write("Important: this script preserves source rows except exact duplicate rows removed from geography.\n")
        f.write("It does not filter orders by date or silently discard unmatched returns.\n\n")
        f.write("Output row counts:\n")
        for item in counts:
            f.write(f"- {item['file']}: {item['rows']} rows, {item['columns']} columns\n")
        f.write("\nWarnings and validation notes:\n")
        if audit:
            for line in audit:
                f.write(f"- {line}\n")
        else:
            f.write("- No warnings recorded.\n")
        f.write("\nReview every audit_*.csv file before using the data in SQL Server.\n")

    print(f"Done. Cleaned CSVs and audit files saved to: {outdir.resolve()}")
    print(f"Orders: {len(orders):,} (source: {raw_counts['orders']:,})")
    print(f"Order items: {len(items):,} (source: {raw_counts['order_items']:,})")
    print(f"Returns: {len(returns):,} (source: {raw_counts['returns']:,})")
    print(f"Shipments: {len(shipment_out):,} (source: {raw_counts['shipments']:,})")
    print(f"Read audit report: {outdir / 'audit_report.txt'}")


if __name__ == "__main__":
    main()
