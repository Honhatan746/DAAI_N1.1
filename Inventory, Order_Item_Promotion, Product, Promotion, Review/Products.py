import pandas as pd
import numpy as np

def clean_product_data(file_path='/content/products.csv'):
    """
    Cleans and standardizes product data from a CSV file based on 3NF schema.

    Args:
        file_path (str): Path to the product CSV file.

    Returns:
        pandas.DataFrame: The cleaned DataFrame.
    """
    print(f"Starting data cleaning for {file_path}")

    # Load the data
    try:
        df = pd.read_csv(file_path)
        print(f"Initial number of rows: {len(df)}")
    except FileNotFoundError:
        print(f"Error: {file_path} not found. Please ensure the file is uploaded.")
        return pd.DataFrame() # Return empty DataFrame on error

    df_original_rows = len(df.index)
    
    # Initialize counters for dropped rows
    dropped_rows_invalid_id = 0
    dropped_rows_pk_duplicates = 0
    dropped_rows_total_before_final = 0

    # 2. XỬ LÝ LỖI SAI KIỂU DỮ LIỆU & RÁC DỮ LIỆU:
    # --- Cột product_id ---
    print("\n--- Processing product_id (PK) ---")
    initial_rows_id_processing = len(df)
    df['product_id_cleaned'] = pd.to_numeric(df['product_id'], errors='coerce')
    df_cleaned_id = df.dropna(subset=['product_id_cleaned']).copy()
    dropped_rows_invalid_id = initial_rows_id_processing - len(df_cleaned_id)
    
    if dropped_rows_invalid_id > 0:
        print(f"Dropped {dropped_rows_invalid_id} rows due to invalid/null 'product_id'.")
    
    df_cleaned_id['product_id'] = df_cleaned_id['product_id_cleaned'].astype(int)
    df = df_cleaned_id.drop(columns=['product_id_cleaned'])

    # --- Cột giá tiền (price, cogs) ---
    print("\n--- Cleaning Price and COGS ---")
    for col in ['price', 'cogs']:
        if col in df.columns:
            # Convert to string to apply string operations
            df[col] = df[col].astype(str)
            # Remove currency symbols ($, đ, VNĐ) and thousands separators (,)
            df[col] = df[col].str.replace(r'[$,đVNĐ]', '', regex=True)
            df[col] = df[col].str.replace(',', '', regex=False)
            # Convert to numeric, coercing errors to NaN
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # --- Cột text (product_name, category, segment, size, color) ---
    print("\n--- Standardizing Text Columns ---")
    text_cols = ['product_name', 'category', 'segment', 'size', 'color']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({'nan': 'Unknown', 'null': 'Unknown', '': 'Unknown'})
            # Optional: Capitalize first letter as in previous request, or other consistent casing
            df[col] = df[col].str.capitalize() 
            
    print(f"Current rows after data type and garbage cleaning: {len(df)}")

    # 3. KIỂM TRA LOGIC NGHIỆP VỤ & LÀM SẠCH:
    # --- Loại bỏ trùng lặp (drop_duplicates) theo PK product_id ---
    print("\n--- Handling Duplicates and Business Logic ---")
    initial_rows_before_dedup = len(df)
    df.drop_duplicates(subset=['product_id'], keep='first', inplace=True)
    dropped_rows_pk_duplicates = initial_rows_before_dedup - len(df)
    if dropped_rows_pk_duplicates > 0:
        print(f"Dropped {dropped_rows_pk_duplicates} rows due to duplicate 'product_id'.")

    # --- Logic giá: price >= 0 và cogs >= 0. Nếu âm, chuyển về giá trị tuyệt đối. ---
    for col in ['price', 'cogs']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: abs(x) if pd.notnull(x) and x < 0 else x)
            
    # --- Điền thiếu (Imputation): price bị NaN thì fill bằng median của chính `category` đó. ---
    if 'price' in df.columns and 'category' in df.columns:
        # Fill price NaNs with median of its category
        df['price'] = df.groupby('category')['price'].transform(lambda x: x.fillna(x.median()))
        # Fill any remaining price NaNs (e.g., if category median was also NaN) with global median or 0
        df['price'] = df['price'].fillna(df['price'].median() if pd.notna(df['price'].median()) else 0.0)

    # --- Điền thiếu (Imputation): cogs bị NaN thì fill bằng 60% của price. ---
    if 'cogs' in df.columns and 'price' in df.columns:
        df['cogs'] = df.apply(lambda row: row['price'] * 0.6 if pd.isna(row['cogs']) and pd.notna(row['price']) else row['cogs'], axis=1)
        df['cogs'] = df['cogs'].fillna(0.0) # Fill any remaining cogs NaNs

    # --- Logic biên lợi nhuận: Kiểm tra cogs > price. Nếu có, log cảnh báo (không drop ngay mà có thể set cogs = price * 0.7 hoặc giữ nguyên tùy cờ cấu hình). ---
    if 'cogs' in df.columns and 'price' in df.columns:
        cogs_higher_than_price = df[(df['cogs'] > df['price']) & pd.notna(df['cogs']) & pd.notna(df['price'])]
        if not cogs_higher_than_price.empty:
            print(f"Warning: {len(cogs_higher_than_price)} rows have 'cogs' greater than 'price'.")
            # Example of adjustment (uncomment if desired by user, for now, just logging as requested)
            # df.loc[cogs_higher_than_price.index, 'cogs'] = df.loc[cogs_higher_than_price.index, 'price'] * 0.7
            
    print(f"Current rows after business logic application: {len(df)}")

    # 4. OUTPUT:
    # --- In log: Số dòng ban đầu, số dòng lỗi kiểu dữ liệu bị loại, số dòng trùng lặp bị xóa, số dòng hợp lệ cuối cùng. ---
    final_rows = len(df)
    total_dropped_rows = df_original_rows - final_rows
    
    print(f"\n--- Data Cleaning Summary ---")
    print(f"Số dòng ban đầu: {df_original_rows}")
    print(f"Số dòng lỗi kiểu dữ liệu/null product_id bị loại: {dropped_rows_invalid_id}")
    print(f"Số dòng trùng lặp product_id bị xóa: {dropped_rows_pk_duplicates}")
    print(f"Tổng số dòng bị loại bỏ: {total_dropped_rows}")
    print(f"Số dòng hợp lệ cuối cùng: {final_rows}")

    # --- Lưu file: `clean_product.csv` (index=False). ---
    output_file = 'clean_product.csv'
    df.to_csv(output_file, index=False)
    print(f"Cleaned data saved to {output_file}")
    print(f"\nCleaned DataFrame head:")
    display(df.head())

    return df

# --- Call the function to run the cleaning process ---
cleaned_df = clean_product_data()