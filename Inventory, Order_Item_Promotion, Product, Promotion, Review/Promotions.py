import pandas as pd
import numpy as np
import re

def clean_promotion_data(file_path='/content/promotions.csv'): # Changed to promotions.csv
    """
    Cleans and preprocesses promotion data from a CSV file based on 3NF schema.

    Args:
        file_path (str): Path to the promotion CSV file.

    Returns:
        pandas.DataFrame: The cleaned DataFrame.
    """
    print(f"Starting data cleaning for {file_path}")

    # Opt-in to future pandas behavior to avoid FutureWarning
    pd.set_option('future.no_silent_downcasting', True)

    # Load the data
    try:
        df = pd.read_csv(file_path)
        print(f"Initial number of rows: {len(df)}")
    except FileNotFoundError:
        print(f"Error: {file_path} not found. Please ensure the file is uploaded.")
        return pd.DataFrame() # Return empty DataFrame on error

    df_original_rows = len(df.index)

    # Initialize counters for reporting
    dropped_rows_invalid_id = 0
    dropped_rows_pk_duplicates = 0
    rows_invalid_date_format_na = 0
    rows_date_logic_violation_swapped = 0
    rows_discount_value_adjusted = 0
    rows_stackable_flag_fixed = 0

    # 2. XỬ LÝ LỖI SAI KIỂU DỮ LIỆU:
    # --- promo_id ---
    print("\n--- Processing promo_id (PK) ---")
    print("Original 'promo_id' column head before cleaning:")
    print(df['promo_id'].head())

    initial_rows_id_processing = len(df)

    # Extract numeric part from 'PROMO-XXXX' strings
    df['promo_id_extracted'] = df['promo_id'].astype(str).str.extract(r'(\d+)', expand=False)
    df['promo_id_cleaned'] = pd.to_numeric(df['promo_id_extracted'], errors='coerce')

    print("'promo_id_extracted' column head after regex extraction:")
    print(df['promo_id_extracted'].head())
    print("'promo_id_cleaned' column head after pd.to_numeric:")
    print(df['promo_id_cleaned'].head())
    print(f"Number of NaN values in 'promo_id_cleaned': {df['promo_id_cleaned'].isna().sum()}")

    df_temp = df.dropna(subset=['promo_id_cleaned']).copy() # Use a temp df to calculate drops
    dropped_rows_invalid_id = initial_rows_id_processing - len(df_temp)
    if dropped_rows_invalid_id > 0:
        print(f"Dropped {dropped_rows_invalid_id} rows due to invalid/null 'promo_id' after extraction.")
    df = df_temp # Update df after dropping

    if not df.empty:
        df['promo_id'] = df['promo_id_cleaned'].astype(int) # Overwrite original promo_id with cleaned int
        df.drop(columns=['promo_id_cleaned', 'promo_id_extracted'], inplace=True)
    else:
        print("DataFrame is empty after promo_id cleaning, skipping further processing.")
        return pd.DataFrame() # Exit early if no data remains

    initial_rows_before_dedup = len(df)
    df.drop_duplicates(subset=['promo_id'], keep='first', inplace=True)
    dropped_rows_pk_duplicates = initial_rows_before_dedup - len(df)
    if dropped_rows_pk_duplicates > 0:
        print(f"Dropped {dropped_rows_pk_duplicates} rows due to duplicate 'promo_id'.")
    print(f"Current rows after promo_id cleaning: {len(df)}")

    # --- start_date, end_date ---
    print("\n--- Processing Dates (start_date, end_date) ---")
    # Convert to datetime, coerce errors to NaT
    df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce')
    df['end_date'] = pd.to_datetime(df['end_date'], errors='coerce')

    # Count and drop rows with NaT dates
    rows_invalid_date_format_na = df['start_date'].isna().sum() + df['end_date'].isna().sum()
    if rows_invalid_date_format_na > 0:
        print(f"Warning: {rows_invalid_date_format_na} date values were unparseable and converted to NaT.")

    # --- stackable_flag ---
    print("\n--- Standardizing stackable_flag ---")
    if 'stackable_flag' in df.columns:
        original_stackable_flag = df['stackable_flag'].copy()
        df['stackable_flag'] = df['stackable_flag'].astype(str).str.lower().replace({
            'true': True, '1': True, 'yes': True, 'y': True,
            'false': False, '0': False, 'no': False, 'n': False,
            'nan': False, '': False, 'null': False # Default for empty/unknown
        })
        # Ensure all are boolean type
        df['stackable_flag'] = df['stackable_flag'].astype(bool)
        rows_stackable_flag_fixed = (original_stackable_flag != df['stackable_flag']).sum()
        if rows_stackable_flag_fixed > 0:
            print(f"Corrected {rows_stackable_flag_fixed} rows for 'stackable_flag' format errors.")

    # --- discount_value, min_order_value ---
    print("\n--- Cleaning Numeric Values (discount_value, min_order_value) ---")
    for col in ['discount_value', 'min_order_value']:
        if col in df.columns:
            df[col] = df[col].astype(str)
            # Remove %, currency symbols, and thousands separators
            df[col] = df[col].str.replace('%', '', regex=False)
            df[col] = df[col].str.replace(r'[$,đVNĐ]', '', regex=True)
            df[col] = df[col].str.replace(',', '', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    print(f"Current rows after data type cleaning: {len(df)}")

    # 3. KIỂM TRA LOGIC NGHIỆP VỤ:
    print("\n--- Applying Business Logic ---")
    # --- Logic ngày: start_date <= end_date ---
    # Identify rows where end_date < start_date
    invalid_date_logic_mask = (df['start_date'].notna()) & (df['end_date'].notna()) & (df['end_date'] < df['start_date'])
    rows_date_logic_violation_swapped = invalid_date_logic_mask.sum()

    if rows_date_logic_violation_swapped > 0:
        print(f"Warning: Found {rows_date_logic_violation_swapped} rows where end_date < start_date. Swapping dates.")
        # Swap start_date and end_date for invalid logic
        df.loc[invalid_date_logic_mask, ['start_date', 'end_date']] = df.loc[invalid_date_logic_mask, ['end_date', 'start_date']].values

    # --- Logic giảm giá: discount_value >= 0. Nếu promo_type là 'Percentage' thì discount_value (0, 100]. ---
    if 'discount_value' in df.columns:
        df['discount_value'] = df['discount_value'].apply(lambda x: max(0.0, x)) # Ensure >= 0

        if 'promo_type' in df.columns:
            percentage_promos_mask = df['promo_type'].str.contains('percentage', case=False, na=False)
            # Check for discount_value > 100 for percentage type
            invalid_percentage_mask = percentage_promos_mask & (df['discount_value'] > 100)
            rows_discount_value_adjusted += invalid_percentage_mask.sum()
            if invalid_percentage_mask.sum() > 0:
                print(f"Warning: Found {invalid_percentage_mask.sum()} 'Percentage' promos with discount_value > 100. Setting to 100.")
                df.loc[invalid_percentage_mask, 'discount_value'] = 100.0
            # Check for discount_value <= 0 (already handled by max(0.0,x) but can be re-checked for percentage logic if 0 is not desired)
            zero_percentage_mask = percentage_promos_mask & (df['discount_value'] <= 0)
            if zero_percentage_mask.sum() > 0:
                print(f"Warning: Found {zero_percentage_mask.sum()} 'Percentage' promos with discount_value <= 0. Consider adjusting if 0 is not valid.")

    # --- min_order_value >= 0 ---
    if 'min_order_value' in df.columns:
        df['min_order_value'] = df['min_order_value'].apply(lambda x: max(0.0, x))

    # --- Các cột text còn lại fill 'General' hoặc 'Unknown' nếu null ---
    text_cols_fill = ['promo_name', 'promo_type', 'applicable_category', 'promo_channel']
    for col in text_cols_fill:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({'nan': 'General', 'null': 'General', '': 'General'})
            df[col] = df[col].fillna('General') # Catch any remaining NaN

    print(f"Current rows after business logic application: {len(df)}")

    # 4. OUTPUT:
    final_rows = len(df)
    total_dropped_rows = df_original_rows - final_rows

    print(f"\n--- Data Cleaning Summary ---")
    print(f"Số dòng ban đầu: {df_original_rows}")
    print(f"Số dòng 'promo_id' không hợp lệ/null bị loại: {dropped_rows_invalid_id}")
    print(f"Số dòng 'promo_id' trùng lặp bị xóa: {dropped_rows_pk_duplicates}")
    # print(f"Số dòng có định dạng ngày không parse được: {rows_invalid_date_format_na}") # This is count of values, not rows
    print(f"Số dòng vi phạm logic ngày tháng (end_date < start_date) đã được hoán đổi: {rows_date_logic_violation_swapped}")
    print(f"Số dòng 'stackable_flag' bị sửa định dạng: {rows_stackable_flag_fixed}")
    print(f"Số dòng 'discount_value' phần trăm > 100% đã điều chỉnh: {rows_discount_value_adjusted}")
    print(f"Tổng số dòng bị loại bỏ: {total_dropped_rows}")
    print(f"Số dòng hợp lệ cuối cùng: {final_rows}")

    # --- Lưu file: `clean_promotion.csv` (index=False, format date YYYY-MM-DD). ---
    output_file = 'clean_promotion.csv'
    # Format dates to YYYY-MM-DD string before saving
    if 'start_date' in df.columns and pd.api.types.is_datetime64_any_dtype(df['start_date']):
        df['start_date'] = df['start_date'].dt.strftime('%Y-%m-%d')
    if 'end_date' in df.columns and pd.api.types.is_datetime64_any_dtype(df['end_date']):
        df['end_date'] = df['end_date'].dt.strftime('%Y-%m-%d')

    df.to_csv(output_file, index=False)
    print(f"Cleaned data saved to {output_file}")
    print(f"\nCleaned DataFrame head:")
    display(df.head())

    return df

# --- Call the function to run the cleaning process ---
cleaned_promotion_df = clean_promotion_data()