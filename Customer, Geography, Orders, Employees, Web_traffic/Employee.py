import pandas as pd
import numpy as np
import re

def clean_employee_data(orders_file_path='/content/orders_enriched.csv'):
    """
    Extracts, cleans and validates employee data from the denormalized
    orders_enriched.csv file (one employee can appear on many order rows).

    Args:
        orders_file_path (str): Path to the orders_enriched CSV file.

    Returns:
        pandas.DataFrame: The cleaned, deduplicated EMPLOYEE DataFrame.
    """
    print(f"Starting data cleaning for employee from {orders_file_path}")

    # Opt-in to future pandas behavior to avoid FutureWarning
    pd.set_option('future.no_silent_downcasting', True)

    # 1. Load the data
    try:
        df = pd.read_csv(orders_file_path)
        print(f"Initial number of rows in orders_enriched: {len(df)}")
    except FileNotFoundError:
        print(f"Error: {orders_file_path} not found. Please ensure the file is uploaded.")
        return pd.DataFrame()  # Return empty DataFrame on error

    # Only keep the columns that belong to the EMPLOYEE table
    employee_cols = ["sales_employee_id", "sales_employee_name", "marital_status", "education_level", "years_experience"]
    df = df[[c for c in employee_cols if c in df.columns]].copy()

    df_original_rows = len(df.index)

    # Initialize counters for reporting
    dropped_rows_invalid_employee_id = 0
    dropped_rows_pk_duplicates = 0
    years_experience_values_adjusted_negative = 0

    # 2. XỬ LÝ LỖI KIỂU DỮ LIỆU & RÁC:

    # --- sales_employee_id (Primary Key, dinh dang 'EMP####') ---
    print("\n--- Processing sales_employee_id ---")
    initial_rows_id_processing = len(df)
    df['sales_employee_id'] = df['sales_employee_id'].astype(str).str.strip()
    valid_id_mask = df['sales_employee_id'].str.match(r'^EMP\d+$')
    df_temp = df[valid_id_mask].copy()
    dropped_rows_invalid_employee_id = initial_rows_id_processing - len(df_temp)
    if dropped_rows_invalid_employee_id > 0:
        print(f"Dropped {dropped_rows_invalid_employee_id} rows due to invalid/null 'sales_employee_id' (must match EMP + digits).")
    df = df_temp

    if df.empty:
        print("DataFrame is empty after sales_employee_id cleaning, skipping further processing.")
        return pd.DataFrame()

    # --- sales_employee_name ---
    print("\n--- Processing sales_employee_name ---")
    if 'sales_employee_name' in df.columns:
        df['sales_employee_name'] = df['sales_employee_name'].astype(str).apply(lambda s: " ".join(s.strip().split()))
        print("Cleaned 'sales_employee_name' column (whitespace stripped/collapsed).")

    # --- marital_status / education_level ---
    print("\n--- Processing marital_status and education_level ---")
    for col in ['marital_status', 'education_level']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            print(f"Cleaned '{col}' column (whitespace stripped).")

    # --- years_experience ---
    print("\n--- Cleaning years_experience Column ---")
    if 'years_experience' in df.columns:
        df['years_experience'] = pd.to_numeric(df['years_experience'], errors='coerce')
        df['years_experience'] = df['years_experience'].fillna(0)
        print(f"Cleaned 'years_experience' column. Head: {df['years_experience'].head().tolist()}")

    print(f"Current rows after data type and garbage cleaning: {len(df)}")

    # 3. KIỂM TRA LOGIC & KHÓA:

    # --- Logic số học: years_experience phải >= 0. Nếu âm thì gán = 0. ---
    print("\n--- Applying Numeric Logic (>= 0) ---")
    if 'years_experience' in df.columns:
        original_negative_count = (df['years_experience'] < 0).sum()
        if original_negative_count > 0:
            print(f"Found {original_negative_count} negative values in 'years_experience'. Setting to 0.")
            df['years_experience'] = df['years_experience'].apply(lambda x: max(0, x))
            years_experience_values_adjusted_negative += original_negative_count
        df['years_experience'] = df['years_experience'].astype(int)

    # --- Primary Key (sales_employee_id) duplicates: 1 dong dai dien cho moi employee ---
    print("\n--- Handling Primary Key Duplicates (dedup to 1 row per employee) ---")
    initial_rows_before_pk_dedup = len(df)
    df.drop_duplicates(subset=['sales_employee_id'], keep='first', inplace=True)
    dropped_rows_pk_duplicates = initial_rows_before_pk_dedup - len(df)
    if dropped_rows_pk_duplicates > 0:
        print(f"Dropped {dropped_rows_pk_duplicates} rows due to duplicate 'sales_employee_id' (PK), keeping first occurrence.")
    df = df.sort_values('sales_employee_id').reset_index(drop=True)
    print(f"Current rows after PK deduplication: {len(df)}")

    # 4. OUTPUT:
    final_rows = len(df)
    total_dropped_rows = df_original_rows - final_rows

    print(f"\n--- Data Cleaning Summary for Employee ---")
    print(f"Số dòng ban đầu: {df_original_rows}")
    print(f"Số dòng 'sales_employee_id' không hợp lệ/null bị loại: {dropped_rows_invalid_employee_id}")
    print(f"Số dòng trùng lặp PK (sales_employee_id) bị xóa (dedup): {dropped_rows_pk_duplicates}")
    print(f"Số giá trị 'years_experience' âm đã được điều chỉnh thành 0: {years_experience_values_adjusted_negative}")
    print(f"Tổng số dòng bị loại bỏ: {total_dropped_rows}")
    print(f"Số nhân viên (dòng) hợp lệ cuối cùng: {final_rows}")

    # --- Lưu file: `clean_employee.csv` (index=False). ---
    output_file = 'clean_employee.csv'
    df.to_csv(output_file, index=False)
    print(f"Cleaned data saved to {output_file}")
    print(f"\nCleaned DataFrame head:")
    print(df.head())

    return df

if __name__ == '__main__':
    # --- Call the function to run the cleaning process ---
    cleaned_employee_df = clean_employee_data()
