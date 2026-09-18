import pandas as pd
import numpy as np
import re

def clean_orders_data(orders_file_path='/content/orders_enriched.csv',
                       customer_ref_file_path='/content/customer_clean.csv',
                       employee_ref_file_path='/content/employee_clean.csv',
                       geography_ref_file_path='/content/geography_clean.csv'):
    """
    Cleans and validates orders data from a CSV file.

    Args:
        orders_file_path (str): Path to the orders CSV file.
        customer_ref_file_path (str): Path to the cleaned customer reference CSV file.
        employee_ref_file_path (str): Path to the cleaned employee reference CSV file.
        geography_ref_file_path (str): Path to the cleaned geography reference CSV file.

    Returns:
        pandas.DataFrame: The cleaned DataFrame.
    """
    print(f"Starting data cleaning for orders from {orders_file_path}")

    # Opt-in to future pandas behavior to avoid FutureWarning
    pd.set_option('future.no_silent_downcasting', True)

    # 1. Load the data
    try:
        df = pd.read_csv(orders_file_path)
        print(f"Initial number of rows in orders: {len(df)}")
    except FileNotFoundError:
        print(f"Error: {orders_file_path} not found. Please ensure the file is uploaded.")
        return pd.DataFrame()  # Return empty DataFrame on error

    # Only keep the columns that belong to the ORDERS table
    order_cols = ["order_id", "order_date", "order_status", "device_type", "order_source", "comment", "customer_id", "sales_employee_id", "zip"]
    df = df[[c for c in order_cols if c in df.columns]].copy()

    df_original_rows = len(df.index)

    # Load valid reference ids for FK validation
    try:
        customer_ref_df = pd.read_csv(customer_ref_file_path)
        valid_customer_ids = customer_ref_df['customer_id'].astype(str).str.strip().unique()
        print(f"Loaded {len(valid_customer_ids)} valid customer_ids from {customer_ref_file_path}")
    except FileNotFoundError:
        print(f"Error: {customer_ref_file_path} not found. Cannot perform FK validation for customer_id.")
        valid_customer_ids = np.array([])

    try:
        employee_ref_df = pd.read_csv(employee_ref_file_path)
        valid_employee_ids = employee_ref_df['sales_employee_id'].astype(str).str.strip().unique()
        print(f"Loaded {len(valid_employee_ids)} valid sales_employee_ids from {employee_ref_file_path}")
    except FileNotFoundError:
        print(f"Error: {employee_ref_file_path} not found. Cannot perform FK validation for sales_employee_id.")
        valid_employee_ids = np.array([])

    try:
        geography_ref_df = pd.read_csv(geography_ref_file_path)
        valid_zips = geography_ref_df['zip'].astype(str).str.strip().unique()
        print(f"Loaded {len(valid_zips)} valid zip codes from {geography_ref_file_path}")
    except FileNotFoundError:
        print(f"Error: {geography_ref_file_path} not found. Cannot perform FK validation for delivery_zip.")
        valid_zips = np.array([])

    # Initialize counters for reporting
    dropped_rows_invalid_order_id = 0
    dropped_rows_invalid_date = 0
    dropped_rows_pk_duplicates = 0
    dropped_rows_fk_orphan_customer = 0
    dropped_rows_fk_orphan_employee = 0
    dropped_rows_fk_orphan_geography = 0

    # 2. XỬ LÝ LỖI KIỂU DỮ LIỆU & RÁC:

    # --- order_id (Primary Key) ---
    print("\n--- Processing order_id ---")
    initial_rows_order_id_processing = len(df)
    df['order_id_cleaned'] = pd.to_numeric(df['order_id'], errors='coerce')
    df_temp = df.dropna(subset=['order_id_cleaned']).copy()
    dropped_rows_invalid_order_id = initial_rows_order_id_processing - len(df_temp)
    if dropped_rows_invalid_order_id > 0:
        print(f"Dropped {dropped_rows_invalid_order_id} rows due to invalid/null 'order_id'.")
    df = df_temp

    if not df.empty:
        df['order_id'] = df['order_id_cleaned'].astype(int)
        df.drop(columns=['order_id_cleaned'], inplace=True)
    else:
        print("DataFrame is empty after order_id cleaning, skipping further processing.")
        return pd.DataFrame()

    # --- order_date ---
    print("\n--- Processing order_date ---")
    initial_rows_date_processing = len(df)
    df['order_date_cleaned'] = pd.to_datetime(df['order_date'], errors='coerce')
    df_temp = df.dropna(subset=['order_date_cleaned']).copy()
    dropped_rows_invalid_date = initial_rows_date_processing - len(df_temp)
    if dropped_rows_invalid_date > 0:
        print(f"Dropped {dropped_rows_invalid_date} rows due to invalid/null 'order_date'.")
    df = df_temp

    if not df.empty:
        df['order_date'] = df['order_date_cleaned'].dt.strftime('%Y-%m-%d')
        df.drop(columns=['order_date_cleaned'], inplace=True)
    else:
        print("DataFrame is empty after order_date cleaning, skipping further processing.")
        return pd.DataFrame()

    print(f"Current rows after order_id and order_date cleaning: {len(df)}")

    # --- Primary Key (order_id) duplicates ---
    print("\n--- Handling Primary Key Duplicates ---")
    initial_rows_before_pk_dedup = len(df)
    df.drop_duplicates(subset=['order_id'], keep='first', inplace=True)
    dropped_rows_pk_duplicates = initial_rows_before_pk_dedup - len(df)
    if dropped_rows_pk_duplicates > 0:
        print(f"Dropped {dropped_rows_pk_duplicates} rows due to duplicate 'order_id' (PK).")
    print(f"Current rows after PK deduplication: {len(df)}")

    # --- Các cột chuỗi (order_status, device_type, order_source, comment) ---
    print("\n--- Cleaning String Columns ---")
    string_cols = ['order_status', 'device_type', 'order_source', 'comment']
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            print(f"Cleaned '{col}' column (whitespace stripped).")

    # --- Đổi tên cột 'zip' -> 'delivery_zip' theo schema chuẩn ---
    if 'zip' in df.columns:
        df['delivery_zip'] = df['zip'].astype(str).str.strip()
        df.drop(columns=['zip'], inplace=True)

    # --- customer_id / sales_employee_id (chuẩn hóa dạng chuỗi để đối chiếu FK) ---
    for col in ['customer_id', 'sales_employee_id']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    print(f"Current rows after data type and garbage cleaning: {len(df)}")

    # 3. KIỂM TRA LOGIC & KHÓA NGOẠI (REFERENTIAL INTEGRITY):

    # --- ĐỐI CHIẾU KHÓA NGOẠI: customer_id -> CUSTOMER.customer_id ---
    print("\n--- Performing Foreign Key (customer_id) Validation ---")
    if not df.empty and len(valid_customer_ids) > 0:
        initial_rows_fk_check = len(df)
        df_filtered = df[df['customer_id'].isin(valid_customer_ids)].copy()
        dropped_rows_fk_orphan_customer = initial_rows_fk_check - len(df_filtered)
        if dropped_rows_fk_orphan_customer > 0:
            print(f"Dropped {dropped_rows_fk_orphan_customer} rows due to 'customer_id' not found in customer_clean.csv (orphan FK).")
        df = df_filtered
    elif not df.empty and len(valid_customer_ids) == 0:
        print("Warning: No valid customer_ids loaded for FK validation. Skipping customer_id FK check.")

    # --- ĐỐI CHIẾU KHÓA NGOẠI: sales_employee_id -> EMPLOYEE.sales_employee_id ---
    print("\n--- Performing Foreign Key (sales_employee_id) Validation ---")
    if not df.empty and len(valid_employee_ids) > 0:
        initial_rows_fk_check = len(df)
        df_filtered = df[df['sales_employee_id'].isin(valid_employee_ids)].copy()
        dropped_rows_fk_orphan_employee = initial_rows_fk_check - len(df_filtered)
        if dropped_rows_fk_orphan_employee > 0:
            print(f"Dropped {dropped_rows_fk_orphan_employee} rows due to 'sales_employee_id' not found in employee_clean.csv (orphan FK).")
        df = df_filtered
    elif not df.empty and len(valid_employee_ids) == 0:
        print("Warning: No valid sales_employee_ids loaded for FK validation. Skipping sales_employee_id FK check.")

    # --- ĐỐI CHIẾU KHÓA NGOẠI: delivery_zip -> GEOGRAPHY.zip ---
    print("\n--- Performing Foreign Key (delivery_zip) Validation ---")
    if not df.empty and len(valid_zips) > 0:
        initial_rows_fk_check = len(df)
        df_filtered = df[df['delivery_zip'].isin(valid_zips)].copy()
        dropped_rows_fk_orphan_geography = initial_rows_fk_check - len(df_filtered)
        if dropped_rows_fk_orphan_geography > 0:
            print(f"Dropped {dropped_rows_fk_orphan_geography} rows due to 'delivery_zip' not found in geography_clean.csv (orphan FK).")
        df = df_filtered
    elif not df.empty and len(valid_zips) == 0:
        print("Warning: No valid zip codes loaded for FK validation. Skipping delivery_zip FK check.")

    print(f"Current rows after FK validation: {len(df)}")

    # 4. OUTPUT:
    final_rows = len(df)
    total_dropped_rows = df_original_rows - final_rows

    print(f"\n--- Data Cleaning Summary for Orders ---")
    print(f"Số dòng ban đầu: {df_original_rows}")
    print(f"Số dòng 'order_id' không hợp lệ/null bị loại: {dropped_rows_invalid_order_id}")
    print(f"Số dòng 'order_date' không hợp lệ/null bị loại: {dropped_rows_invalid_date}")
    print(f"Số dòng trùng lặp PK (order_id) bị xóa: {dropped_rows_pk_duplicates}")
    print(f"Số dòng bị loại bỏ do FK 'customer_id' mồ côi: {dropped_rows_fk_orphan_customer}")
    print(f"Số dòng bị loại bỏ do FK 'sales_employee_id' mồ côi: {dropped_rows_fk_orphan_employee}")
    print(f"Số dòng bị loại bỏ do FK 'delivery_zip' mồ côi: {dropped_rows_fk_orphan_geography}")
    print(f"Tổng số dòng bị loại bỏ: {total_dropped_rows}")
    print(f"Số dòng hợp lệ cuối cùng: {final_rows}")

    # --- Lưu file: `clean_orders.csv` (index=False). ---
    output_file = 'clean_orders.csv'
    df.to_csv(output_file, index=False)
    print(f"Cleaned data saved to {output_file}")
    print(f"\nCleaned DataFrame head:")
    print(df.head())

    return df

if __name__ == '__main__':
    # --- Call the function to run the cleaning process ---
    cleaned_orders_df = clean_orders_data()
