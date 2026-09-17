import pandas as pd
import os

# Tạo thư mục xuất dữ liệu nếu chưa có
output_dir = "export"
os.makedirs(output_dir, exist_ok=True)

print("--- XỬ LÝ BẢNG PAYMENT ---")

# 1. Đảm bảo Toàn vẹn tham chiếu (Referential Integrity)
# Đọc danh sách order_id hợp lệ từ bảng gốc ORDERS để làm mốc đối chiếu
df_orders = pd.read_csv("orders_enriched.csv", low_memory=False)
valid_order_ids = set(df_orders['order_id'].astype(int))

# Đọc dữ liệu Payments
df_pay = pd.read_csv("payments.csv", low_memory=False)

# Lọc bỏ các payment mồ côi (có order_id nhưng không tồn tại trong danh sách đơn hàng)
df_pay = df_pay[df_pay['order_id'].isin(valid_order_ids)] 

# 2. Xử lý vi phạm và dị biệt dữ liệu
# Đảm bảo quan hệ 1-1 giữa Order và Payment: Xóa các bản ghi trùng lặp order_id
df_pay = df_pay.drop_duplicates(subset=['order_id']).copy()

# Phương án làm sạch dữ liệu (Data Cleansing):
# - payment_value: Số tiền không thể âm. Nếu gặp số âm (lỗi hệ thống), gán về 0.
df_pay['payment_value'] = df_pay['payment_value'].apply(lambda x: x if pd.notnull(x) and x >= 0 else 0)

# - installments: Số kỳ trả góp mặc định là 1 (trả thẳng). Điền 1 cho các dòng null hoặc < 1.
df_pay['installments'] = df_pay['installments'].fillna(1).apply(lambda x: x if pd.notnull(x) and x >= 1 else 1)

# 3. Xuất file kết quả
out_path = os.path.join(output_dir, "clean_payment.csv")
df_pay.to_csv(out_path, index=False)
print(f"Đã xuất: {out_path} ({len(df_pay):,} dòng)")