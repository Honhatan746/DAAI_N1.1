import pandas as pd
import numpy as np
import re

def clean_web_traffic_data(web_traffic_file_path='/content/web_traffic.csv'):
    """
    Cleans and validates web traffic data from a CSV file.

    Args:
        web_traffic_file_path (str): Path to the web_traffic CSV file.

    Returns:
        pandas.DataFrame: The cleaned DataFrame.
    """
    print(f"Starting data cleaning for web traffic from {web_traffic_file_path}")

    # Opt-in to future pandas behavior to avoid FutureWarning
    pd.set_option('future.no_silent_downcasting', True)

    # 1. Load the data
    try:
        df = pd.read_csv(web_traffic_file_path)
        print(f"Initial number of rows in web_traffic: {len(df)}")
    except FileNotFoundError:
        print(f"Error: {web_traffic_file_path} not found. Please ensure the file is uploaded.")
        return pd.DataFrame()  # Return empty DataFrame on error

    df_original_rows = len(df.index)

    # Initialize counters for reporting
    dropped_rows_invalid_date = 0
    dropped_rows_invalid_source = 0
    dropped_rows_pk_duplicates = 0
    numeric_values_adjusted_negative = 0
    numeric_values_adjusted_unparseable = 0

    # 2. XỬ LÝ LỖI KIỂU DỮ LIỆU & RÁC:

    # --- traffic_date (source column may be named 'date') ---
    print("\n--- Processing traffic_date ---")
    date_source_col = 'traffic_date' if 'traffic_date' in df.columns else 'date'
    initial_rows_date_processing = len(df)
    df['traffic_date_cleaned'] = pd.to_datetime(df[date_source_col], errors='coerce')
    df_temp = df.dropna(subset=['traffic_date_cleaned']).copy()
    dropped_rows_invalid_date = initial_rows_date_processing - len(df_temp)
    if dropped_rows_invalid_date > 0:
        print(f"Dropped {dropped_rows_invalid_date} rows due to invalid/null '{date_source_col}'.")
    df = df_temp

    if not df.empty:
        df['traffic_date'] = df['traffic_date_cleaned'].dt.strftime('%Y-%m-%d')
        df.drop(columns=['traffic_date_cleaned'], inplace=True)
        if date_source_col != 'traffic_date' and date_source_col in df.columns:
            df.drop(columns=[date_source_col], inplace=True)
    else:
        print("DataFrame is empty after traffic_date cleaning, skipping further processing.")
        return pd.DataFrame()

    # --- traffic_source ---
    print("\n--- Processing traffic_source ---")
    initial_rows_source_processing = len(df)
    df['traffic_source'] = df['traffic_source'].astype(str).str.strip()
    invalid_source_tokens = {'', 'nan', 'none', 'null', 'n/a', 'na', '-'}
    df_temp = df[~df['traffic_source'].str.lower().isin(invalid_source_tokens)].copy()
    dropped_rows_invalid_source = initial_rows_source_processing - len(df_temp)
    if dropped_rows_invalid_source > 0:
        print(f"Dropped {dropped_rows_invalid_source} rows due to invalid/null 'traffic_source'.")
    df = df_temp

    if df.empty:
        print("DataFrame is empty after traffic_source cleaning, skipping further processing.")
        return pd.DataFrame()

    print(f"Current rows after traffic_date and traffic_source cleaning: {len(df)}")

    # --- Composite PK (traffic_date, traffic_source) ---
    print("\n--- Handling Composite PK Duplicates ---")
    initial_rows_before_pk_dedup = len(df)
    df.drop_duplicates(subset=['traffic_date', 'traffic_source'], keep='first', inplace=True)
    dropped_rows_pk_duplicates = initial_rows_before_pk_dedup - len(df)
    if dropped_rows_pk_duplicates > 0:
        print(f"Dropped {dropped_rows_pk_duplicates} rows due to duplicate composite PK (traffic_date, traffic_source).")
    print(f"Current rows after composite PK deduplication: {len(df)}")

    # --- Các cột số (sessions, unique_visitors, page_views, bounce_rate, avg_session_duration_sec) ---
    print("\n--- Cleaning Numeric Columns ---")
    numeric_cols = ['sessions', 'unique_visitors', 'page_views', 'bounce_rate', 'avg_session_duration_sec']
    for col in numeric_cols:
        if col in df.columns:
            parsed = pd.to_numeric(df[col], errors='coerce')
            n_unparseable = parsed.isna().sum()
            if n_unparseable > 0:
                print(f"'{col}': {n_unparseable} value(s) could not be parsed as a number, setting to 0.")
                numeric_values_adjusted_unparseable += n_unparseable
            df[col] = parsed.fillna(0)
            print(f"Cleaned '{col}' column. Head: {df[col].head().tolist()}")

    print(f"Current rows after data type and garbage cleaning: {len(df)}")

    # 3. KIỂM TRA LOGIC & RÀNG BUỘC:

    # --- Logic số học: Tất cả các cột số phải >= 0. Nếu âm thì gán = 0. ---
    print("\n--- Applying Numeric Logic (>= 0) ---")
    non_negative_cols = ['sessions', 'unique_visitors', 'page_views', 'avg_session_duration_sec']
    for col in non_negative_cols:
        if col in df.columns:
            original_negative_count = (df[col] < 0).sum()
            if original_negative_count > 0:
                print(f"Found {original_negative_count} negative values in '{col}'. Setting to 0.")
                df[col] = df[col].apply(lambda x: max(0, x))
                numeric_values_adjusted_negative += original_negative_count

    # --- Ràng buộc bounce_rate: phải nằm trong khoảng [0, 1] (dạng tỷ lệ thập phân) ---
    print("\n--- Enforcing bounce_rate Constraint [0, 1] ---")
    if 'bounce_rate' in df.columns:
        out_of_range_mask = (df['bounce_rate'] < 0) | (df['bounce_rate'] > 1)
        n_out_of_range = out_of_range_mask.sum()
        if n_out_of_range > 0:
            print(f"Found {n_out_of_range} 'bounce_rate' values outside [0, 1]. Clipping to range.")
            df['bounce_rate'] = df['bounce_rate'].clip(lower=0, upper=1)
            numeric_values_adjusted_negative += n_out_of_range

    # --- Cast integer-like columns to int ---
    for col in ['sessions', 'unique_visitors', 'page_views', 'avg_session_duration_sec']:
        if col in df.columns:
            df[col] = df[col].astype(int)

    print(f"Current rows after business logic application: {len(df)}")

    # 4. OUTPUT:
    final_rows = len(df)
    total_dropped_rows = df_original_rows - final_rows

    print(f"\n--- Data Cleaning Summary for Web Traffic ---")
    print(f"Số dòng ban đầu: {df_original_rows}")
    print(f"Số dòng 'traffic_date' không hợp lệ/null bị loại: {dropped_rows_invalid_date}")
    print(f"Số dòng 'traffic_source' không hợp lệ/null bị loại: {dropped_rows_invalid_source}")
    print(f"Số dòng trùng lặp PK phức hợp bị xóa: {dropped_rows_pk_duplicates}")
    print(f"Số giá trị số không parse được đã được điều chỉnh thành 0: {numeric_values_adjusted_unparseable}")
    print(f"Số giá trị số âm/ngoài khoảng đã được điều chỉnh: {numeric_values_adjusted_negative}")
    print(f"Tổng số dòng bị loại bỏ: {total_dropped_rows}")
    print(f"Số dòng hợp lệ cuối cùng: {final_rows}")

    # --- Lưu file: `clean_web_traffic.csv` (index=False). ---
    output_file = 'clean_web_traffic.csv'
    df.to_csv(output_file, index=False)
    print(f"Cleaned data saved to {output_file}")
    print(f"\nCleaned DataFrame head:")
    print(df.head())

    return df

if __name__ == '__main__':
    # --- Call the function to run the cleaning process ---
    cleaned_web_traffic_df = clean_web_traffic_data()
