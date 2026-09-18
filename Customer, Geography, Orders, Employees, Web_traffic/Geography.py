import pandas as pd

# ============================================================
# CẤU HÌNH
# ============================================================

INPUT_FILE = "geography.csv"
OUTPUT_FILE = "clean_geography.csv"

TARGET_COLUMNS = ["zip", "city", "region", "district"]

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
# ĐỌC DỮ LIỆU
# ============================================================

def load_data():
    df = pd.read_csv(
        INPUT_FILE,
        dtype=str,
        keep_default_na=False
    )

    print("=" * 60)
    print("ĐỌC DỮ LIỆU")
    print("=" * 60)
    print(f"Số dòng: {len(df)}")
    print(f"Số cột: {len(df.columns)}")
    print(f"Cột: {df.columns.tolist()}")

    return df


# ============================================================
# CHUẨN HÓA GIÁ TRỊ RỖNG
# ============================================================

def normalize_missing_values(df):
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

        df[col] = df[col].apply(
            lambda x: "" if x.lower() in MISSING_VALUES else x
        )

    return df


# ============================================================
# KIỂM TRA PRIMARY KEY: ZIP
# ============================================================

def check_primary_key(df):
    print("\n" + "=" * 60)
    print("KIỂM TRA PRIMARY KEY: zip")
    print("=" * 60)

    # ZIP rỗng
    missing_zip = df["zip"] == ""

    # ZIP không phải số
    invalid_zip = (
        (df["zip"] != "") &
        (~df["zip"].str.match(r"^\d+$"))
    )

    # ZIP bị trùng
    duplicate_zip = (
        df["zip"].duplicated(keep=False) &
        (df["zip"] != "")
    )

    print(f"ZIP rỗng/null: {missing_zip.sum()}")
    print(f"ZIP không hợp lệ: {invalid_zip.sum()}")
    print(f"ZIP bị trùng: {duplicate_zip.sum()}")

    return missing_zip, invalid_zip, duplicate_zip


# ============================================================
# KIỂM TRA ZIP NGẮN HƠN 5 SỐ
# ============================================================

def check_zip_format(df):
    print("\n" + "=" * 60)
    print("KIỂM TRA ĐỊNH DẠNG ZIP")
    print("=" * 60)

    valid_zip = (
        (df["zip"] != "") &
        (df["zip"].str.match(r"^\d+$"))
    )

    short_zip = valid_zip & (df["zip"].str.len() < 5)

    print(f"ZIP ngắn hơn 5 ký tự: {short_zip.sum()}")

    if short_zip.sum() > 0:
        print("Các ZIP nghi ngờ:")
        print(df.loc[short_zip, "zip"].tolist())

    return short_zip


# ============================================================
# KIỂM TRA GIÁ TRỊ RỖNG
# ============================================================

def check_missing_values(df):
    print("\n" + "=" * 60)
    print("KIỂM TRA NULL / RỖNG")
    print("=" * 60)

    for col in TARGET_COLUMNS:
        count = (df[col] == "").sum()
        print(f"{col}: {count}")


# ============================================================
# KIỂM TRA TÍNH NHẤT QUÁN CITY / DISTRICT -> REGION
# ============================================================

def check_consistency(df):
    print("\n" + "=" * 60)
    print("KIỂM TRA TÍNH NHẤT QUÁN ĐỊA DANH")
    print("=" * 60)

    for col in ["city", "district"]:

        # Bỏ các dòng thiếu dữ liệu trước khi kiểm tra
        temp = df[
            (df[col] != "") &
            (df["region"] != "")
        ]

        mapping = temp.groupby(col)["region"].nunique()

        inconsistent = mapping[mapping > 1]

        print(
            f"{col} ánh xạ tới nhiều region: "
            f"{len(inconsistent)}"
        )

        if len(inconsistent) > 0:
            print(inconsistent)


# ============================================================
# LÀM SẠCH DỮ LIỆU
# ============================================================

def clean_geography(df):
    print("\n" + "=" * 60)
    print("TẠO CLEAN DATA")
    print("=" * 60)

    # --------------------------------------------------------
    # 1. Chuẩn hóa khoảng trắng
    # --------------------------------------------------------

    for col in TARGET_COLUMNS:
        df[col] = df[col].astype(str).str.strip()

    # --------------------------------------------------------
    # 2. Chuyển các giá trị missing thành chuỗi rỗng
    # --------------------------------------------------------

    df = normalize_missing_values(df)

    # --------------------------------------------------------
    # 3. ZIP bắt buộc phải tồn tại
    # --------------------------------------------------------

    valid_zip = (
        (df["zip"] != "") &
        (df["zip"].str.match(r"^\d+$"))
    )

    df = df[valid_zip].copy()

    # --------------------------------------------------------
    # 4. Chỉ giữ ZIP duy nhất
    # --------------------------------------------------------
    #
    # Nếu ZIP trùng nhưng dữ liệu city/region/district
    # khác nhau thì không tự chọn một dòng.
    #
    # Để tạo bảng GEOGRAPHY hợp lệ với PK = zip,
    # loại các ZIP bị trùng khỏi file clean.
    # --------------------------------------------------------

    duplicate_zip = df["zip"].duplicated(keep=False)

    df = df[~duplicate_zip].copy()

    # --------------------------------------------------------
    # 5. Xóa dòng trùng hoàn toàn
    #
    # Phần này chủ yếu để đảm bảo dữ liệu sạch.
    # --------------------------------------------------------

    df = df.drop_duplicates()

    # --------------------------------------------------------
    # 6. Giữ nguyên cấu trúc cột
    # --------------------------------------------------------

    df = df[TARGET_COLUMNS]

    return df


# ============================================================
# MAIN
# ============================================================

def main():

    # Đọc dữ liệu gốc
    df = load_data()

    original_columns = df.columns.tolist()
    original_rows = len(df)

    # Kiểm tra dữ liệu trước khi clean
    check_missing_values(df)

    check_primary_key(df)

    check_zip_format(df)

    check_consistency(df)

    # Làm sạch
    df_clean = clean_geography(df)

    # ========================================================
    # KIỂM TRA CẤU TRÚC
    # ========================================================

    if df_clean.columns.tolist() != original_columns:
        print("\nLỖI: Cấu trúc cột đã bị thay đổi!")
        print("Cột ban đầu:", original_columns)
        print("Cột sau clean:", df_clean.columns.tolist())
        return

    # Kiểm tra lại PK
    if df_clean["zip"].duplicated().any():
        print("\nLỖI: ZIP vẫn còn bị trùng!")
        return

    if (df_clean["zip"] == "").any():
        print("\nLỖI: ZIP vẫn còn giá trị rỗng!")
        return

    # ========================================================
    # XUẤT FILE
    # ========================================================

    df_clean.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\n" + "=" * 60)
    print("HOÀN THÀNH")
    print("=" * 60)

    print(f"Số dòng ban đầu : {original_rows}")
    print(f"Số dòng sau clean: {len(df_clean)}")
    print(f"Số dòng bị loại : {original_rows - len(df_clean)}")
    print(f"File output      : {OUTPUT_FILE}")
    print(f"Cột              : {df_clean.columns.tolist()}")


# ============================================================
# CHẠY CHƯƠNG TRÌNH
# ============================================================

if __name__ == "__main__":
    main()