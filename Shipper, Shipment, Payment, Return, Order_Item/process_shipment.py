import pandas as pd
import os

output_dir = "export"
os.makedirs(output_dir, exist_ok=True)

print("--- XỬ LÝ BẢNG SHIPMENT ---")

# 1. Toàn vẹn tham chiếu
df_orders = pd.read_csv("orders_enriched.csv", low_memory=False)
valid_order_ids = set(df_orders['order_id'].astype(int))

df_ship = pd.read_csv("shipments_realistic.csv", low_memory=False)
df_ship = df_ship[df_ship['order_id'].isin(valid_order_ids)]

# 2. Chuẩn hóa 3NF: Tách thực thể SHIPMENT
# Chỉ chọn các cột mô tả sự kiện giao hàng (Fact Table)
shipment_cols = ['order_id', 'shipper_id', 'ship_date', 'delivery_date', 'shipping_fee']

# Lọc bỏ các chuyến giao trùng lặp trên cùng 1 đơn hàng (giả định 1 order_id = 1 shipment)
clean_shipment = df_ship[shipment_cols].drop_duplicates(subset=['order_id']).copy()

# Sinh khóa chính nhân tạo (Surrogate Key) `shipment_id` cho bảng
clean_shipment.insert(0, 'shipment_id', range(1, len(clean_shipment) + 1))

# 3. Xuất file kết quả
out_path = os.path.join(output_dir, "clean_shipment.csv")
clean_shipment.to_csv(out_path, index=False)
print(f"Đã xuất: {out_path} ({len(clean_shipment):,} dòng) - Quản lý nghiệp vụ giao vận")