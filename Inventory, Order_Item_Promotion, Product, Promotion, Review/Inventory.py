import pandas as pd
import numpy as np
import re

def clean_inventory_data(inventory_file_path='/content/inventory.csv', product_ref_file_path='/content/clean_product.csv'):
    """
    Cleans and validates inventory data from a CSV file.

    Args:
        inventory_file_path (str): Path to the inventory CSV file.
        product_ref_file_path (str): Path to the cleaned product reference CSV file.

    Returns:
        pandas.DataFrame: The cleaned DataFrame.
    """
    print(f"Starting data cleaning for inventory from {inventory_file_path}")

    # Opt-in to future pandas behavior to avoid FutureWarning
    pd.set_option('future.no_silent_downcasting', True)

    # 1. Load the data
    try:
        df = pd.read_csv(inventory_file_path)
        print(f"Initial number of rows in inventory: {len(df)}")
    except FileNotFoundError:
        print(f"Error: {inventory_file_path} not found. Please ensure the file is uploaded.")
        return pd.DataFrame() # Return empty DataFrame on error

    df_original_rows = len(df.index)

    # Load valid product_ids for FK validation
    try:
        product_ref_df = pd.read_csv(product_ref_file_path)
        valid_product_ids = product_ref_df['product_id'].unique()
        print(f"Loaded {len(valid_product_ids)} valid product_ids from {product_ref_file_path}")
    except FileNotFoundError:
        print(f"Error: {product_ref_file_path} not found. Cannot perform FK validation.")
        valid_product_ids = np.array([]) # Empty array if reference file not found

    # Initialize counters for reporting
    dropped_rows_invalid_product_id = 0
    dropped_rows_invalid_date = 0
    dropped_rows_pk_duplicates = 0
    dropped_rows_fk_orphan = 0
    qty_values_adjusted_negative = 0
    stockout_flag_adjusted = 0

    # 2. XỬ LÝ LỖI KIỂU DỮ LIỆU & RÁC:

    # --- product_id ---
    print("\n--- Processing product_id ---")
    initial_rows_product_id_processing = len(df)
    df['product_id_cleaned'] = pd.to_numeric(df['product_id'], errors='coerce')
    df_temp = df.dropna(subset=['product_id_cleaned']).copy()
    dropped_rows_invalid_product_id = initial_rows_product_id_processing - len(df_temp)
    if dropped_rows_invalid_product_id > 0:
        print(f"Dropped {dropped_rows_invalid_product_id} rows due to invalid/null 'product_id'.")
    df = df_temp

    if not df.empty:
        df['product_id'] = df['product_id_cleaned'].astype(int)
        df.drop(columns=['product_id_cleaned'], inplace=True)
    else:
        print("DataFrame is empty after product_id cleaning, skipping further processing.")
        return pd.DataFrame()

    # --- snapshot_date ---
    print("\n--- Processing snapshot_date ---")
    initial_rows_date_processing = len(df)
    df['snapshot_date_cleaned'] = pd.to_datetime(df['snapshot_date'], errors='coerce')
    df_temp = df.dropna(subset=['snapshot_date_cleaned']).copy()
    dropped_rows_invalid_date = initial_rows_date_processing - len(df_temp)
    if dropped_rows_invalid_date > 0:
        print(f"Dropped {dropped_rows_invalid_date} rows due to invalid/null 'snapshot_date'.")
    df = df_temp

    if not df.empty:
        df['snapshot_date'] = df['snapshot_date_cleaned'].dt.strftime('%Y-%m-%d')
        df.drop(columns=['snapshot_date_cleaned'], inplace=True)
    else:
        print("DataFrame is empty after snapshot_date cleaning, skipping further processing.")
        return pd.DataFrame()

    print(f"Current rows after product_id and snapshot_date cleaning: {len(df)}")

    # --- Composite PK (product_id, snapshot_date) ---
    print("\n--- Handling Composite PK Duplicates ---")
    initial_rows_before_pk_dedup = len(df)
    df.drop_duplicates(subset=['product_id', 'snapshot_date'], keep='first', inplace=True)
    dropped_rows_pk_duplicates = initial_rows_before_pk_dedup - len(df)
    if dropped_rows_pk_duplicates > 0:
        print(f"Dropped {dropped_rows_pk_duplicates} rows due to duplicate composite PK (product_id, snapshot_date).")
    print(f"Current rows after composite PK deduplication: {len(df)}")

    # --- Các cột số lượng (stock_on_hand, units_received, units_sold, stockout_days) ---
    print("\n--- Cleaning Quantity Columns ---")
    qty_cols = ['stock_on_hand', 'units_received', 'units_sold', 'stockout_days']
    for col in qty_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.lower() # Convert to string for consistent handling
            # Extract numeric parts first, then convert to numeric
            # Handle cases like '10pcs' -> 10, 'OOS' -> NaN, 'None' -> NaN
            df[col] = df[col].apply(lambda x: re.search(r'\d+', x).group(0) if re.search(r'\d+', x) else x)
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].fillna(0).astype(int)
            print(f"Cleaned '{col}' column. Head: {df[col].head().tolist()}")

    print(f"Current rows after data type and garbage cleaning: {len(df)}")

    # 3. KIỂM TRA LOGIC & KHÓA NGOẠI (REFERENTIAL INTEGRITY):

    # --- Logic số học: Tất cả các cột số lượng phải >= 0. Nếu âm thì gán = 0. ---
    print("\n--- Applying Numeric Logic (>= 0) ---")
    for col in qty_cols:
        if col in df.columns:
            original_negative_count = (df[col] < 0).sum()
            if original_negative_count > 0:
                print(f"Found {original_negative_count} negative values in '{col}'. Setting to 0.")
                df[col] = df[col].apply(lambda x: max(0, x))
                qty_values_adjusted_negative += original_negative_count

    # --- Logic cờ hết hàng: stockout_flag ---
    print("\n--- Enforcing stockout_flag Logic ---")
    if 'stock_on_hand' in df.columns and 'stockout_days' in df.columns and 'stockout_flag' in df.columns:
        # Ensure stockout_flag is boolean type first
        df['stockout_flag'] = df['stockout_flag'].astype(str).str.lower().replace({
            'true': True, '1': True, 'yes': True, 'y': True,
            'false': False, '0': False, 'no': False, 'n': False,
            'nan': False, '': False, 'null': False
        }).astype(bool)

        # Determine the correct stockout_flag based on logic
        new_stockout_flag = ((df['stock_on_hand'] == 0) | (df['stockout_days'] > 0))

        # Count discrepancies and apply correction
        discrepancy_mask = (df['stockout_flag'] != new_stockout_flag)
        stockout_flag_adjusted = discrepancy_mask.sum()

        if stockout_flag_adjusted > 0:
            print(f"Adjusted 'stockout_flag' for {stockout_flag_adjusted} rows to match stock_on_hand and stockout_days logic.")
            df.loc[discrepancy_mask, 'stockout_flag'] = new_stockout_flag

    print(f"Current rows after business logic application: {len(df)}")

    # --- ĐỐI CHIẾU KHÓA NGOẠI (Referential Integrity) ---
    print("\n--- Performing Foreign Key (product_id) Validation ---")
    if not df.empty and len(valid_product_ids) > 0:
        initial_rows_fk_check = len(df)
        df_filtered = df[df['product_id'].isin(valid_product_ids)].copy()
        dropped_rows_fk_orphan = initial_rows_fk_check - len(df_filtered)
        if dropped_rows_fk_orphan > 0:
            print(f"Dropped {dropped_rows_fk_orphan} rows due to 'product_id' not found in clean_product.csv (orphan FK).")
        df = df_filtered
    elif not df.empty and len(valid_product_ids) == 0:
        print("Warning: No valid product_ids loaded for FK validation. Skipping FK check.")

    print(f"Current rows after FK validation: {len(df)}")

    # 4. OUTPUT:
    final_rows = len(df)
    total_dropped_rows = df_original_rows - final_rows

    print(f"\n--- Data Cleaning Summary for Inventory ---")
    print(f"Số dòng ban đầu: {df_original_rows}")
    print(f"Số dòng 'product_id' không hợp lệ/null bị loại: {dropped_rows_invalid_product_id}")
    print(f"Số dòng 'snapshot_date' không hợp lệ/null bị loại: {dropped_rows_invalid_date}")
    print(f"Số dòng trùng lặp PK phức hợp bị xóa: {dropped_rows_pk_duplicates}")
    print(f"Số dòng bị loại bỏ do FK mồ côi (product_id không tồn tại): {dropped_rows_fk_orphan}")
    print(f"Số giá trị số lượng âm đã được điều chỉnh thành 0: {qty_values_adjusted_negative}")
    print(f"Số dòng 'stockout_flag' đã được điều chỉnh: {stockout_flag_adjusted}")
    print(f"Tổng số dòng bị loại bỏ: {total_dropped_rows}")
    print(f"Số dòng hợp lệ cuối cùng: {final_rows}")

    # --- Lưu file: `clean_inventory.csv` (index=False). ---
    output_file = 'clean_inventory.csv'
    df.to_csv(output_file, index=False)
    print(f"Cleaned data saved to {output_file}")
    print(f"\nCleaned DataFrame head:")
    display(df.head())

    return df

if __name__ == '__main__':
    # --- Call the function to run the cleaning process ---
    cleaned_inventory_df = clean_inventory_data()