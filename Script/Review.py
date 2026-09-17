import pandas as pd
import numpy as np
import re

def clean_id_series(series):
    """
    Hàm trích xuất số nguyên an toàn từ chuỗi hoặc số:
    - Loại bỏ khoảng trắng thừa.
    - Dùng Regex tìm cụm số liên tục đầu tiên (ví dụ 'REV_00123' -> 123).
    - Trả về Series kiểu Int64 (hỗ trợ nullable integer).
    """
    # Ép chuỗi, strip khoảng trắng
    s_str = series.astype(str).str.strip()
    # Tìm cụm chữ số đầu tiên
    extracted = s_str.str.extract(r'(\d+)', expand=False)
    return pd.to_numeric(extracted, errors='coerce')


def clean_review_data(review_file_path='/content/reviews.csv',
                      customer_ref_file_path='/content/customers.csv',
                      product_ref_file_path='/content/clean_product.csv'):

    print(f"Starting data cleaning for reviews from {review_file_path}")

    # 1. INPUT: Load the data
    try:
        df = pd.read_csv(review_file_path)
        # Chuẩn hóa tên cột (loại bỏ space thừa, đưa về chữ thường)
        df.columns = df.columns.str.strip().str.lower()
        print(f"Initial number of rows in reviews: {len(df)}")
        print(f"Detected columns: {df.columns.tolist()}")
    except FileNotFoundError:
        print(f"Error: {review_file_path} not found. Please ensure the file is uploaded.")
        return pd.DataFrame()

    df_original_rows = len(df.index)

    # 2. LOAD & NORMALIZE REFERENCE PARENT IDs (DÙNG SET ĐỂ TĂNG TỐC O(1))
    valid_customer_ids = set()
    try:
        customer_ref_df = pd.read_csv(customer_ref_file_path)
        customer_ref_df.columns = customer_ref_df.columns.str.strip().str.lower()
        cust_clean = clean_id_series(customer_ref_df['customer_id']).dropna()
        valid_customer_ids = set(cust_clean.astype(int))
        print(f"Loaded {len(valid_customer_ids)} valid customer_ids from {customer_ref_file_path}")
    except Exception as e:
        print(f"Error loading {customer_ref_file_path}: {e}")

    valid_product_ids = set()
    try:
        product_ref_df = pd.read_csv(product_ref_file_path)
        product_ref_df.columns = product_ref_df.columns.str.strip().str.lower()
        prod_clean = clean_id_series(product_ref_df['product_id']).dropna()
        valid_product_ids = set(prod_clean.astype(int))
        print(f"Loaded {len(valid_product_ids)} valid product_ids from {product_ref_file_path}")
    except Exception as e:
        print(f"Error loading {product_ref_file_path}: {e}")

    # 3. XỬ LÝ CÁC CỘT ID (review_id, customer_id, product_id)
    print("\n--- Processing IDs (review_id, customer_id, product_id) ---")
    id_cols = ['review_id', 'customer_id', 'product_id']

    for col in id_cols:
        if col not in df.columns:
            print(f"CRITICAL ERROR: Column '{col}' not found in CSV. Existing columns: {df.columns.tolist()}")
            return pd.DataFrame()

        initial_len = len(df)
        df[col] = clean_id_series(df[col])

        # Chỉ loại bỏ các dòng thực sự không thể tách ra số (NaN)
        df = df.dropna(subset=[col]).copy()
        dropped = initial_len - len(df)
        df[col] = df[col].astype(int)
        print(f"Column '{col}': Dropped {dropped} unrecoverable invalid rows. Remaining: {len(df)}")

    if df.empty:
        print("DataFrame is empty after ID extraction.")
        return pd.DataFrame()

    # --- drop_duplicates theo review_id (Khóa chính PK) ---
    print("\n--- Handling Duplicate review_id ---")
    initial_before_dedup = len(df)
    df = df.drop_duplicates(subset=['review_id'], keep='first')
    pk_duplicates = initial_before_dedup - len(df)
    print(f"Dropped {pk_duplicates} rows due to duplicate 'review_id'. Current: {len(df)}")

    # --- review_date ---
    print("\n--- Processing review_date ---")
    if 'review_date' in df.columns:
        initial_date_len = len(df)
        df['parsed_date'] = pd.to_datetime(df['review_date'], errors='coerce')
        # Bỏ các dòng ngày sai định dạng/chứa ký tự vô nghĩa không parse được
        df = df.dropna(subset=['parsed_date']).copy()
        dropped_dates = initial_date_len - len(df)
        df['review_date'] = df['parsed_date'].dt.strftime('%Y-%m-%d')
        df.drop(columns=['parsed_date'], inplace=True)
        print(f"Dropped {dropped_dates} rows with invalid dates. Current: {len(df)}")

    # --- rating ---
    print("\n--- Standardizing rating ---")
    if 'rating' in df.columns:
        # Bóc tách số, nếu null điền 5, kẹp trong đoạn [1, 5]
        extracted_ratings = clean_id_series(df['rating'])
        df['rating'] = extracted_ratings.fillna(5).astype(int).clip(1, 5)

    # --- review_title ---
    if 'review_title' in df.columns:
        df['review_title'] = df['review_title'].fillna('').astype(str).str.strip()

    # 4. KIỂM TRA TOÀN VẸN KHÓA NGOẠI (DUAL FK VALIDATION)
    print("\n--- Performing Dual Foreign Key Validation ---")
    initial_fk_check = len(df)

    # Đối chiếu nhanh qua set()
    mask_cust = df['customer_id'].isin(valid_customer_ids)
    mask_prod = df['product_id'].isin(valid_product_ids)

    invalid_cust_count = (~mask_cust).sum()
    invalid_prod_count = (~mask_prod).sum()

    if invalid_cust_count > 0:
        print(f"  - {invalid_cust_count} rows have customer_id not in customers.csv")
    if invalid_prod_count > 0:
        print(f"  - {invalid_prod_count} rows have product_id not in clean_product.csv")

    df = df[mask_cust & mask_prod].copy()
    dropped_fk = initial_fk_check - len(df)
    print(f"Total dropped due to orphan Foreign Keys: {dropped_fk}. Current: {len(df)}")

    # 5. OUTPUT
    output_file = '/content/clean_review.csv'
    df.to_csv(output_file, index=False)
    print("\n" + "=" * 50)
    print(f"SUMMARY REPORT FOR REVIEWS:")
    print(f"- Initial records: {df_original_rows}")
    print(f"- Final clean records: {len(df)}")
    print(f"- Saved clean data to: {output_file}")
    print("=" * 50)

    return df

if __name__ == '__main__':
    # Chạy làm sạch
    cleaned_review_df = clean_review_data()
    if not cleaned_review_df.empty:
        print("\nCleaned DataFrame head:")
        print(cleaned_review_df.head().to_markdown(index=False))