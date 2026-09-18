import pandas as pd
import os

output_dir = "export"
os.makedirs(output_dir, exist_ok=True)

print("--- XỬ LÝ BẢNG RETURN ---")

# 1. Toàn vẹn tham chiếu
df_orders = pd.read_csv("orders_enriched.csv", low_memory=False)
valid_order_ids = set(df_orders['order_id'].astype(int))

df_ret = pd.read_csv("returns.csv", low_memory=False)
df_ret = df_ret[df_ret['order_id'].isin(valid_order_ids)]

# 2. Xây dựng lại khóa liên kết (Foreign Key Mapping)
# Đọc file order_items (nguyên bản) để mô phỏng lại order_item_id
# Lưu ý: Code này chạy độc lập nên tự tạo lại cấu trúc ID giống script số 4
df_oi = pd.read_csv("order_items.csv", low_memory=False)
df_oi = df_oi[df_oi['order_id'].isin(valid_order_ids)]
df_oi.insert(0, 'order_item_id', range(1, len(df_oi) + 1))

# Dùng cặp (order_id, product_id) để tra cứu lấy mã order_item_id tương ứng
clean_return = df_ret.merge(df_oi[['order_id', 'product_id', 'order_item_id']], 
                            on=['order_id', 'product_id'], 
                            how='left')

# 3. Lọc cột theo cấu trúc chuẩn
ret_cols = ['return_id', 'order_id', 'order_item_id', 'return_date', 'return_reason', 'return_quantity', 'refund_amount']
clean_return = clean_return[ret_cols].copy()

# Xuất file kết quả
out_path = os.path.join(output_dir, "clean_return.csv")
clean_return.to_csv(out_path, index=False)
print(f"Đã xuất: {out_path} ({len(clean_return):,} dòng) - Map thành công ID chi tiết đơn hàng")