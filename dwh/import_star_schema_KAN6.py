import os
import time
import pyodbc
import pandas as pd
import numpy as np

# Database connection parameters
SERVER = r".\SQLEXPRESS"
DATABASE = "EcommerceDW"
DATA_DIR = os.path.join(os.path.dirname(__file__), "star_schema_output")

CONN_STR = f"DRIVER={{SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;"

TABLES_ORDER = [
    ("DIM_SHIPPER", "DIM_SHIPPER.csv", [
        "shipper_key", "shipper_id", "shipper_company", "shipper_vehicle", "shipper_rating", "delivery_success_rate", "shipper_experience_years"
    ]),
    # 2. Fact tables,
    ("FACT_PAYMENT", "FACT_PAYMENT.csv", [
        "payment_key", "customer_key", "order_id", "payment_method", "payment_value", "installments"
    ]),
    ("FACT_SHIPMENT", "FACT_SHIPMENT.csv", [
        "ship_date_key", "delivery_date_key", "customer_key", "geography_key", "shipper_key",
        "shipment_id", "order_id", "shipping_fee", "delivery_days"
    ]),
    # 3. Bridge table
]

# Order to delete data (Child tables first)
DELETE_ORDER = []

def clean_value(val):
    if pd.isna(val):
        return None
    return val

def main():
    print(f"[*] Kết nối tới SQL Server: {SERVER}, Database: {DATABASE}...")
    conn = pyodbc.connect(CONN_STR, autocommit=False)
    cursor = conn.cursor()

    # Step 1: Ensure FACT_PAYMENT table structure matches new CSV
    print("[*] Kiểm tra cấu trúc bảng FACT_PAYMENT...")
    cursor.execute("""
        SELECT c.name 
        FROM sys.columns c 
        JOIN sys.tables t ON c.object_id = t.object_id 
        WHERE t.name = 'FACT_PAYMENT' AND c.name = 'payment_key';
    """)
    has_payment_key = cursor.fetchone() is not None

    if not has_payment_key:
        print("    -> FACT_PAYMENT chưa có payment_key, tiến hành DROP và CREATE lại FACT_PAYMENT...")
        cursor.execute("IF OBJECT_ID('dbo.FACT_PAYMENT', 'U') IS NOT NULL DROP TABLE dbo.FACT_PAYMENT;")
        cursor.execute("""
            CREATE TABLE dbo.FACT_PAYMENT (
                payment_key      INT             NOT NULL PRIMARY KEY,
                customer_key     INT             NOT NULL,
                order_id         VARCHAR(50)     NOT NULL,
                payment_method   NVARCHAR(100)   NULL,
                payment_value    DECIMAL(19,4)   NOT NULL,
                installments     INT             NULL,

                CONSTRAINT FK_PAYMENT_CUSTOMER
                    FOREIGN KEY (customer_key)
                    REFERENCES dbo.DIM_CUSTOMER(customer_key)
            );
        """)
        conn.commit()
        print("    -> Đã tạo lại FACT_PAYMENT thành công!")

    # Step 2: Xóa hết dữ liệu trong từng bảng
    print("\n[*] Đang xóa hết dữ liệu trong từng bảng theo thứ tự khóa ngoại...")
    for tbl in DELETE_ORDER:
        t0 = time.time()
        cursor.execute(f"DELETE FROM dbo.{tbl};")
        conn.commit()
        print(f"    - Đã xóa sạch dữ liệu bảng {tbl:30s} ({time.time()-t0:.2f}s)")

    # Step 3: Import dữ liệu mới từ thư mục star_schema_output
    print("\n[*] Đang import dữ liệu từ star_schema_output...")
    total_start = time.time()

    for tbl_name, csv_file, cols in TABLES_ORDER:
        file_path = os.path.join(DATA_DIR, csv_file)
        if not os.path.exists(file_path):
            print(f"    [!] Không tìm thấy file {file_path}, bỏ qua.")
            continue

        t0 = time.time()
        print(f"    - Đang đọc {csv_file}...")
        df = pd.read_csv(file_path, low_memory=False)
        total_rows = len(df)

        # Convert records with clean None handling
        records = [[clean_value(x) for x in row] for row in df[cols].itertuples(index=False)]

        placeholders = ", ".join(["?"] * len(cols))
        col_list = ", ".join(cols)
        sql = f"INSERT INTO dbo.{tbl_name} ({col_list}) VALUES ({placeholders})"

        cursor.fast_executemany = True

        # Process in chunks of 50,000 rows
        chunk_size = 50000
        for i in range(0, total_rows, chunk_size):
            chunk = records[i:i + chunk_size]
            cursor.executemany(sql, chunk)
            conn.commit()

        duration = time.time() - t0
        print(f"      => Đã nạp {total_rows:>7,} dòng vào {tbl_name:28s} ({duration:.2f}s)")

    total_duration = time.time() - total_start
    print(f"\n[*] HOÀN TẤT NẠP TOÀN BỘ DỮ LIỆU trong {total_duration:.2f}s!")

    # Step 4: Kiểm tra lại số lượng dòng trong Database
    print("\n=== THỐNG KÊ SỐ DÒNG SAU KHI IMPORT TRONG DATABASE ===")
    cursor.execute("""
        SELECT t.name AS TableName, p.rows AS TotalRows
        FROM sys.tables t
        JOIN sys.partitions p ON t.object_id = p.object_id
        WHERE p.index_id IN (0, 1)
        ORDER BY p.rows DESC;
    """)
    for row in cursor.fetchall():
        print(f"{row[0]:32s}: {row[1]:>10,} dòng")

    conn.close()

if __name__ == "__main__":
    main()
