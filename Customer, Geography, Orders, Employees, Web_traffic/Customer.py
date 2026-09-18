import pandas as pd


# ============================================================
# CẤU HÌNH
# ============================================================

INPUT_FILE = "customers.csv"
GEOGRAPHY_FILE = "geography_clean.csv"
OUTPUT_FILE = "clean_customers.csv"

# Các giá trị được xem là dữ liệu rỗng
MISSING_VALUES = {
    "",
    "null",
    "none",
    "nan",
    "n/a",
    "na",
    "-"
}


# ============================================================
# ĐỌC FILE
# ============================================================

def load_data():
    print("=" * 70)
    print("ĐỌC DỮ LIỆU CUSTOMER")
    print("=" * 70)

    try:
        df = pd.read_csv(
            INPUT_FILE,
            dtype=str,
            keep_default_na=False
        )

        print(f"Số dòng ban đầu : {len(df)}")
        print(f"Số cột           : {len(df.columns)}")
        print(f"Các cột           : {df.columns.tolist()}")

        return df

    except FileNotFoundError:
        print(f"Không tìm thấy file: {INPUT_FILE}")
        return None


# ============================================================
# CHUẨN HÓA GIÁ TRỊ RỖNG
# ============================================================

def normalize_empty_values(df):
    """
    Chuyển các giá trị biểu diễn NULL/rỗng về chuỗi rỗng.
    Không thêm cột mới.
    """

    for col in df.columns:

        df[col] = df[col].astype(str).str.strip()

        df[col] = df[col].apply(
            lambda x: ""
            if x.lower() in MISSING_VALUES
            else x
        )

    return df


# ============================================================
# KIỂM TRA PRIMARY KEY
# ============================================================

def check_primary_key(df):
    print("\n" + "=" * 70)
    print("KIỂM TRA PRIMARY KEY: customer_id")
    print("=" * 70)

    # NULL / rỗng
    null_pk = (df["customer_id"] == "").sum()

    print(f"customer_id NULL/rỗng : {null_pk}")

    # Không phải số
    numeric_id = pd.to_numeric(
        df["customer_id"],
        errors="coerce"
    )

    invalid_pk = (
        (df["customer_id"] != "")
        & numeric_id.isna()
    ).sum()

    print(f"customer_id không hợp lệ : {invalid_pk}")

    # ID <= 0
    invalid_number = (
        (df["customer_id"] != "")
        & numeric_id.notna()
        & (numeric_id <= 0)
    ).sum()

    print(f"customer_id <= 0 : {invalid_number}")

    # Duplicate
    duplicate_pk = df[
        (df["customer_id"] != "")
        & df["customer_id"].duplicated(keep=False)
    ]

    print(
        f"customer_id bị trùng : {len(duplicate_pk)} dòng"
    )

    return numeric_id


# ============================================================
# KIỂM TRA SIGNUP_DATE
# ============================================================

def check_signup_date(df):
    print("\n" + "=" * 70)
    print("KIỂM TRA signup_date")
    print("=" * 70)

    parsed_date = pd.to_datetime(
        df["signup_date"],
        errors="coerce"
    )

    invalid_date = (
        (df["signup_date"] != "")
        & parsed_date.isna()
    )

    print(
        f"Ngày không hợp lệ : {invalid_date.sum()}"
    )

    print(
        f"Ngày NULL/rỗng : {(df['signup_date'] == '').sum()}"
    )

    return parsed_date


# ============================================================
# KIỂM TRA CÁC CỘT CATEGORICAL
# ============================================================

def check_categorical(df):

    print("\n" + "=" * 70)
    print("KIỂM TRA DỮ LIỆU CATEGORICAL")
    print("=" * 70)

    categorical_columns = [
        "gender",
        "age_group",
        "acquisition_channel"
    ]

    for col in categorical_columns:

        if col not in df.columns:
            continue

        null_count = (df[col] == "").sum()

        print(
            f"{col}: NULL/rỗng = {null_count}"
        )

        print(
            f"Giá trị hiện có: "
            f"{df[col].unique().tolist()}"
        )


# ============================================================
# KIỂM TRA FOREIGN KEY
# ============================================================

def check_foreign_key(df):

    print("\n" + "=" * 70)
    print("KIỂM TRA FOREIGN KEY")
    print("CUSTOMER.zip -> GEOGRAPHY.zip")
    print("=" * 70)

    try:

        geography = pd.read_csv(
            GEOGRAPHY_FILE,
            dtype=str,
            keep_default_na=False
        )

    except FileNotFoundError:

        print(
            f"Không tìm thấy {GEOGRAPHY_FILE}"
        )

        print(
            "Bỏ qua kiểm tra Foreign Key."
        )

        return

    # Chuẩn hóa zip ở bảng Geography
    valid_zip = set(
        geography["zip"]
        .astype(str)
        .str.strip()
    )

    # Chuẩn hóa zip Customer
    customer_zip = (
        df["zip"]
        .astype(str)
        .str.strip()
    )

    # FK NULL
    null_fk = (customer_zip == "").sum()

    # FK không tồn tại bảng cha
    orphan_fk = (
        (customer_zip != "")
        & ~customer_zip.isin(valid_zip)
    ).sum()

    print(f"zip NULL/rỗng : {null_fk}")
    print(f"zip không tồn tại trong GEOGRAPHY : {orphan_fk}")


# ============================================================
# XỬ LÝ CUSTOMER
# ============================================================

def clean_customer(df):

    print("\n" + "=" * 70)
    print("BẮT ĐẦU CLEANING CUSTOMER")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. Loại bỏ khoảng trắng dư thừa
    # --------------------------------------------------------

    df = normalize_empty_values(df)

    # --------------------------------------------------------
    # 2. signup_date
    # --------------------------------------------------------

    parsed_date = pd.to_datetime(
        df["signup_date"],
        errors="coerce"
    )

    # Chỉ chuẩn hóa những ngày parse được
    valid_date = parsed_date.notna()

    df.loc[valid_date, "signup_date"] = (
        parsed_date[valid_date]
        .dt.strftime("%Y-%m-%d")
    )

    # Những ngày không parse được -> rỗng
    invalid_date = (
        (df["signup_date"] != "")
        & parsed_date.isna()
    )

    df.loc[invalid_date, "signup_date"] = ""

    # --------------------------------------------------------
    # 3. CUSTOMER_ID
    # --------------------------------------------------------

    numeric_id = pd.to_numeric(
        df["customer_id"],
        errors="coerce"
    )

    invalid_id = (
        (df["customer_id"] != "")
        & (
            numeric_id.isna()
            | (numeric_id <= 0)
        )
    )

    df.loc[invalid_id, "customer_id"] = ""

    # --------------------------------------------------------
    # 4. Xóa duplicate hoàn toàn giống nhau
    # --------------------------------------------------------

    before_duplicate = len(df)

    df = df.drop_duplicates()

    removed_duplicate = (
        before_duplicate - len(df)
    )

    print(
        f"Duplicate hoàn toàn giống nhau đã xóa: "
        f"{removed_duplicate}"
    )

    # --------------------------------------------------------
    # 5. Duplicate customer_id
    # --------------------------------------------------------

    duplicate_id = (
        (df["customer_id"] != "")
        & df["customer_id"].duplicated(
            keep=False
        )
    )

    print(
        f"Dòng có customer_id trùng nhau: "
        f"{duplicate_id.sum()}"
    )

    # Không tự tạo ID
    # Không tự chọn record nếu dữ liệu khác nhau

    # --------------------------------------------------------
    # 6. Không xóa cột
    # --------------------------------------------------------

    return df


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # Đọc dữ liệu
    # --------------------------------------------------------

    df = load_data()

    if df is None:
        return

    original_columns = df.columns.tolist()
    original_rows = len(df)

    # --------------------------------------------------------
    # Kiểm tra trước khi cleaning
    # --------------------------------------------------------

    check_primary_key(df)

    check_signup_date(df)

    check_categorical(df)

    check_foreign_key(df)

    # --------------------------------------------------------
    # Cleaning
    # --------------------------------------------------------

    df_clean = clean_customer(df)

    # --------------------------------------------------------
    # Kiểm tra cấu trúc
    # --------------------------------------------------------

    if df_clean.columns.tolist() != original_columns:

        print("\nLỖI: Cấu trúc cột đã bị thay đổi!")

        return

    # --------------------------------------------------------
    # Xuất file
    # --------------------------------------------------------

    df_clean.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # Kết quả
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("HOÀN THÀNH CLEANING")
    print("=" * 70)

    print(
        f"Số dòng ban đầu : {original_rows}"
    )

    print(
        f"Số dòng sau cleaning : {len(df_clean)}"
    )

    print(
        f"Số cột : {len(df_clean.columns)}"
    )

    print(
        f"Các cột : {df_clean.columns.tolist()}"
    )

    print(
        f"\nFile đã tạo: {OUTPUT_FILE}"
    )


# ============================================================
# CHẠY CHƯƠNG TRÌNH
# ============================================================

if __name__ == "__main__":
    main()