#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build Star Schema (E-COMMERCE) từ cleaned_output.zip
----------------------------------------------------
Đầu ra (CSV, utf-8-sig để Excel/SQL Server đọc đúng tiếng Việt):
  DIM_DATE, DIM_CUSTOMER, DIM_PRODUCT, DIM_EMPLOYEE, DIM_GEOGRAPHY,
  DIM_PROMOTION, DIM_SHIPPER,
  FACT_SALES_RETURN, FACT_INVENTORY, FACT_PAYMENT, FACT_SHIPMENT,
  BRIDGE_ORDER_ITEM_PROMOTION

Cách chạy:
  python build_star_schema.py --zip cleaned_output.zip --out star_schema_output
  # hoặc nếu đã giải nén:
  python build_star_schema.py --src cleaned_output --out star_schema_output
  # thêm --sqlite để ghi luôn ra file star_schema.db (SQLite)

Yêu cầu: pandas, numpy   (pip install pandas numpy)
"""
import argparse
import io
import sqlite3
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


# ----------------------------------------------------------------------
# 1. Đọc dữ liệu nguồn
# ----------------------------------------------------------------------
def read_csv_from(src_dir: Path | None, zf: zipfile.ZipFile | None, name: str, **kw) -> pd.DataFrame:
    fname = f"clean_{name}.csv"
    if zf is not None:
        member = next(n for n in zf.namelist() if n.endswith("/" + fname) or n == fname)
        with zf.open(member) as f:
            return pd.read_csv(io.TextIOWrapper(f, encoding="utf-8-sig"), low_memory=False, **kw)
    return pd.read_csv(src_dir / fname, encoding="utf-8-sig", low_memory=False, **kw)


def date_key(s: pd.Series) -> pd.Series:
    """'2012-07-04' -> 20120704 (Int64, giữ NA nếu thiếu)."""
    d = pd.to_datetime(s, errors="coerce")
    return (d.dt.year * 10000 + d.dt.month * 100 + d.dt.day).astype("Int64")


def add_sk(df: pd.DataFrame, key_name: str) -> pd.DataFrame:
    """Thêm surrogate key 1..N vào cột đầu tiên."""
    df = df.reset_index(drop=True).copy()
    df.insert(0, key_name, np.arange(1, len(df) + 1, dtype="int64"))
    return df


# ----------------------------------------------------------------------
# 2. Build
# ----------------------------------------------------------------------
def build(src_dir: Path | None, zf: zipfile.ZipFile | None):
    R = lambda n, **kw: read_csv_from(src_dir, zf, n, **kw)

    customers = R("customers")
    employee = R("employee")
    geography = R("geography")
    inventory = R("inventory")
    orders = R("orders")
    order_item = R("order_item")
    oi_promo = R("order_item_promotion")
    payment = R("payment")
    product = R("product")
    promotion = R("promotion")
    ret = R("return")
    shipment = R("shipment")
    shipper = R("shipper")

    # ------------------------------ DIMENSIONS ------------------------------
    # DIM_GEOGRAPHY
    dim_geo = add_sk(geography[["zip", "city", "district", "region"]].drop_duplicates("zip")
                     .sort_values("zip"), "geography_key")

    # DIM_CUSTOMER (giữ địa chỉ đăng ký)
    dim_cus = add_sk(
        customers[["customer_id", "gender", "age_group", "acquisition_channel",
                   "signup_date", "zip", "city"]].sort_values("customer_id"),
        "customer_key")

    # DIM_PRODUCT
    dim_prod = add_sk(
        product[["product_id", "product_name", "category", "segment", "size",
                 "color", "price", "cogs"]].sort_values("product_id"),
        "product_key")

    # DIM_EMPLOYEE
    dim_emp = add_sk(
        employee[["sales_employee_id", "sales_employee_name", "marital_status",
                  "education_level", "years_experience"]].sort_values("sales_employee_id"),
        "employee_key")

    # DIM_PROMOTION
    dim_promo = add_sk(
        promotion[["promo_id", "promo_name", "promo_type", "discount_value", "start_date",
                   "end_date", "applicable_category", "promo_channel", "stackable_flag",
                   "min_order_value"]].sort_values("promo_id"),
        "promotion_key")
    dim_promo["stackable_flag"] = dim_promo["stackable_flag"].astype(str).str.lower().map(
        {"true": 1, "false": 0, "1": 1, "0": 0}).astype("Int64")

    # DIM_SHIPPER (chỉ giữ thuộc tính theo schema, bỏ thông tin cá nhân: tên, sđt, tuổi...)
    dim_ship = add_sk(
        shipper[["shipper_id", "shipper_company", "shipper_vehicle", "shipper_rating",
                 "delivery_success_rate", "shipper_experience_years"]].sort_values("shipper_id"),
        "shipper_key")

    # DIM_DATE: phủ toàn bộ khoảng ngày xuất hiện trong các bảng fact
    all_dates = pd.concat([
        pd.to_datetime(orders["order_date"]),
        pd.to_datetime(shipment["ship_date"]),
        pd.to_datetime(shipment["delivery_date"]),
        pd.to_datetime(inventory["snapshot_date"]),
        pd.to_datetime(ret["return_date"]),
    ]).dropna()
    full = pd.date_range(all_dates.min().replace(month=1, day=1),
                         all_dates.max().replace(month=12, day=31), freq="D")
    dim_date = pd.DataFrame({"full_date": full})
    dim_date.insert(0, "date_key", (full.year * 10000 + full.month * 100 + full.day).astype("int64"))
    dim_date["day"] = full.day
    dim_date["month"] = full.month
    dim_date["month_name"] = full.strftime("%B")
    dim_date["quarter"] = full.quarter
    dim_date["year"] = full.year
    dim_date["weekday"] = full.strftime("%A")
    dim_date["full_date"] = dim_date["full_date"].dt.date

    # ------------------------------ FACT_SALES_RETURN ------------------------------
    # Gộp hoàn trả về mức order_item_id (đúng grain của fact)
    ret_agg = (ret.groupby("order_item_id", as_index=False)
                  .agg(returned_quantity=("return_quantity", "sum"),
                       refund_amount=("refund_amount", "sum"),
                       return_count=("return_id", "count")))

    f = (order_item[["order_item_id", "order_id", "product_id", "quantity",
                     "unit_price", "discount_amount"]]
         .merge(orders[["order_id", "order_date", "order_status", "device_type",
                        "order_source", "customer_id", "sales_employee_id", "delivery_zip"]],
                on="order_id", how="left", validate="m:1")
         .merge(dim_prod[["product_id", "product_key", "cogs"]], on="product_id", how="left", validate="m:1")
         .merge(dim_cus[["customer_id", "customer_key"]], on="customer_id", how="left", validate="m:1")
         .merge(dim_emp[["sales_employee_id", "employee_key"]], on="sales_employee_id", how="left", validate="m:1")
         .merge(dim_geo[["zip", "geography_key"]], left_on="delivery_zip", right_on="zip",
                how="left", validate="m:1")
         .merge(ret_agg, on="order_item_id", how="left", validate="1:1"))

    f["order_date_key"] = date_key(f["order_date"])
    f["gross_amount"] = (f["quantity"] * f["unit_price"]).round(2)
    f["discount_amount"] = f["discount_amount"].fillna(0)
    f["net_amount"] = (f["gross_amount"] - f["discount_amount"]).round(2)
    f["estimated_cost"] = (f["quantity"] * f["cogs"]).round(2)
    f["estimated_profit"] = (f["net_amount"] - f["estimated_cost"]).round(2)
    f["returned_quantity"] = f["returned_quantity"].fillna(0).astype("int64")
    f["refund_amount"] = f["refund_amount"].fillna(0).round(2)
    f["return_count"] = f["return_count"].fillna(0).astype("int64")

    fact_sales = f[["order_date_key", "customer_key", "product_key", "employee_key",
                    "geography_key", "order_id", "order_item_id", "order_status",
                    "device_type", "order_source", "quantity", "unit_price",
                    "gross_amount", "discount_amount", "net_amount", "estimated_cost",
                    "estimated_profit", "returned_quantity", "refund_amount",
                    "return_count"]].sort_values("order_item_id")

    # ------------------------------ FACT_INVENTORY ------------------------------
    fi = inventory.merge(dim_prod[["product_id", "product_key"]], on="product_id",
                         how="left", validate="m:1")
    fi["snapshot_date_key"] = date_key(fi["snapshot_date"])
    for c in ["stockout_flag", "overstock_flag", "reorder_flag"]:
        fi[c] = fi[c].astype(int)
    fact_inv = fi[["snapshot_date_key", "product_key", "stock_on_hand", "units_received",
                   "units_sold", "stockout_days", "days_of_supply", "fill_rate",
                   "stockout_flag", "overstock_flag", "reorder_flag",
                   "sell_through_rate"]].sort_values(["snapshot_date_key", "product_key"])

    # ------------------------------ FACT_PAYMENT ------------------------------
    # clean_payment.csv không có ngày thanh toán -> KHÔNG tạo payment_date_key.
    fp = payment.merge(orders[["order_id", "customer_id"]], on="order_id", how="left", validate="m:1") \
                .merge(dim_cus[["customer_id", "customer_key"]], on="customer_id", how="left", validate="m:1")
    fact_pay = add_sk(fp[["customer_key", "order_id", "payment_method", "payment_value",
                          "installments"]], "payment_key")

    # ------------------------------ FACT_SHIPMENT ------------------------------
    fs = (shipment
          .merge(orders[["order_id", "customer_id", "delivery_zip"]], on="order_id", how="left", validate="m:1")
          .merge(dim_cus[["customer_id", "customer_key"]], on="customer_id", how="left", validate="m:1")
          .merge(dim_geo[["zip", "geography_key"]], left_on="delivery_zip", right_on="zip",
                 how="left", validate="m:1")
          .merge(dim_ship[["shipper_id", "shipper_key"]], on="shipper_id", how="left", validate="m:1"))
    fs["ship_date_key"] = date_key(fs["ship_date"])
    fs["delivery_date_key"] = date_key(fs["delivery_date"])
    fs["delivery_days"] = (pd.to_datetime(fs["delivery_date"]) - pd.to_datetime(fs["ship_date"])).dt.days
    fact_ship = fs[["ship_date_key", "delivery_date_key", "customer_key", "geography_key",
                    "shipper_key", "shipment_id", "order_id", "shipping_fee",
                    "delivery_days"]].sort_values("shipment_id")

    # ------------------------------ BRIDGE ------------------------------
    bridge = (oi_promo.drop_duplicates()
              .merge(dim_promo[["promo_id", "promotion_key"]], on="promo_id", how="left", validate="m:1")
              [["order_item_id", "promotion_key", "promo_id"]]
              .sort_values(["order_item_id", "promotion_key"]))

    tables = {
        "DIM_DATE": dim_date,
        "DIM_CUSTOMER": dim_cus,
        "DIM_PRODUCT": dim_prod,
        "DIM_EMPLOYEE": dim_emp,
        "DIM_GEOGRAPHY": dim_geo,
        "DIM_PROMOTION": dim_promo,
        "DIM_SHIPPER": dim_ship,
        "FACT_SALES_RETURN": fact_sales,
        "FACT_INVENTORY": fact_inv,
        "FACT_PAYMENT": fact_pay,
        "FACT_SHIPMENT": fact_ship,
        "BRIDGE_ORDER_ITEM_PROMOTION": bridge,
    }
    extra = {"ret": ret, "order_item": order_item, "payment": payment,
             "shipment": shipment, "inventory": inventory, "oi_promo": oi_promo}
    return tables, extra


# ----------------------------------------------------------------------
# 3. Kiểm tra chất lượng
# ----------------------------------------------------------------------
def validate(t: dict, x: dict):
    print("\n=== KIỂM TRA ===")
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"[{'OK ' if cond else 'LỖI'}] {name} {detail}")

    fs = t["FACT_SALES_RETURN"]
    check("Số dòng FACT_SALES_RETURN = order_item", len(fs) == len(x["order_item"]), f"({len(fs):,})")
    check("order_item_id duy nhất", fs["order_item_id"].is_unique)
    check("Tổng returned_quantity khớp clean_return",
          fs["returned_quantity"].sum() == x["ret"]["return_quantity"].sum())
    check("Tổng refund_amount khớp clean_return",
          np.isclose(fs["refund_amount"].sum(), x["ret"]["refund_amount"].sum(), atol=1))
    check("return_count khớp số bản ghi return", fs["return_count"].sum() == len(x["ret"]))
    check("FACT_INVENTORY khớp số dòng nguồn", len(t["FACT_INVENTORY"]) == len(x["inventory"]))
    check("FACT_PAYMENT khớp số dòng nguồn", len(t["FACT_PAYMENT"]) == len(x["payment"]))
    check("Tổng payment_value khớp",
          np.isclose(t["FACT_PAYMENT"]["payment_value"].sum(), x["payment"]["payment_value"].sum(), atol=1))
    check("FACT_SHIPMENT khớp số dòng nguồn", len(t["FACT_SHIPMENT"]) == len(x["shipment"]))
    check("Bridge khớp số dòng nguồn", len(t["BRIDGE_ORDER_ITEM_PROMOTION"]) == len(x["oi_promo"].drop_duplicates()))

    # Khóa ngoại không được NULL
    fk_map = {
        "FACT_SALES_RETURN": ["order_date_key", "customer_key", "product_key", "employee_key", "geography_key"],
        "FACT_INVENTORY": ["snapshot_date_key", "product_key"],
        "FACT_PAYMENT": ["customer_key"],
        "FACT_SHIPMENT": ["ship_date_key", "delivery_date_key", "customer_key", "geography_key", "shipper_key"],
        "BRIDGE_ORDER_ITEM_PROMOTION": ["promotion_key"],
    }
    for tb, cols in fk_map.items():
        for c in cols:
            n = int(t[tb][c].isna().sum())
            check(f"{tb}.{c} không NULL", n == 0, f"(NULL={n})")

    # Khóa ngày phải tồn tại trong DIM_DATE
    dk = set(t["DIM_DATE"]["date_key"])
    for tb, cols in [("FACT_SALES_RETURN", ["order_date_key"]),
                     ("FACT_INVENTORY", ["snapshot_date_key"]),
                     ("FACT_SHIPMENT", ["ship_date_key", "delivery_date_key"])]:
        for c in cols:
            check(f"{tb}.{c} có trong DIM_DATE", t[tb][c].dropna().isin(dk).all())

    print("=> TẤT CẢ ĐẠT" if ok else "=> CÓ LỖI, hãy xem lại các dòng [LỖI]")


# ----------------------------------------------------------------------
# 4. Main
# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", default="cleaned_output.zip", help="đường dẫn cleaned_output.zip")
    ap.add_argument("--src", default=None, help="thư mục đã giải nén (nếu dùng thì bỏ qua --zip)")
    ap.add_argument("--out", default="star_schema_output", help="thư mục xuất kết quả")
    ap.add_argument("--sqlite", action="store_true", help="ghi thêm star_schema.db")
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    if a.src:
        tables, extra = build(Path(a.src), None)
    else:
        with zipfile.ZipFile(a.zip) as zf:
            tables, extra = build(None, zf)

    validate(tables, extra)

    print("\n=== GHI FILE (CHI CAC BANG DUOC PHAN CONG) ===")
    assigned_tables = ['DIM_DATE', 'DIM_PRODUCT', 'DIM_PROMOTION', 'FACT_INVENTORY', 'BRIDGE_ORDER_ITEM_PROMOTION']
    for name in assigned_tables:
        df = tables[name]
        df.to_csv(out / f"{name}.csv", index=False, encoding="utf-8-sig")
        print(f"{name:30s} {len(df):>10,} dòng  {df.shape[1]:>2} cột")

    if a.sqlite:
        con = sqlite3.connect(out / "star_schema.db")
        for name, df in tables.items():
            df.to_sql(name, con, if_exists="replace", index=False, chunksize=100_000)
        con.close()
        print(f"\nĐã ghi SQLite: {out / 'star_schema.db'}")

    print(f"\nHoàn tất. Kết quả ở: {out.resolve()}")


if __name__ == "__main__":
    main()
