import pandas as pd
import os

output_dir = "export"
os.makedirs(output_dir, exist_ok=True)

print("--- XỬ LÝ BẢNG SHIPPER ---")

# 1. Đảm bảo Toàn vẹn tham chiếu
df_orders = pd.read_csv("orders_enriched.csv", low_memory=False)
valid_order_ids = set(df_orders['order_id'].astype(int))

df_ship = pd.read_csv("shipments_realistic.csv", low_memory=False)
df_ship = df_ship[df_ship['order_id'].isin(valid_order_ids)]

# 2. Chuẩn hóa 3NF: Tách thực thể SHIPPER
# Chỉ chọn các cột đại diện cho đặc trưng tĩnh và KPI của người giao hàng
shipper_cols = ['shipper_id', 'shipper_company', 'shipper_name', 'shipper_vehicle', 
                'shipper_rating', 'delivery_success_rate', 'shipper_experience_years', 
                'join_date', 'shipper_phone', 'shipper_gender', 'shipper_age', 
                'shipper_marital_status', 'shipper_education']

# Xóa trùng lặp theo shipper_id để tạo bảng danh mục (Dimension Table) duy nhất
clean_shipper = df_ship[shipper_cols].drop_duplicates(subset=['shipper_id']).copy()

# 3. Xuất file kết quả
out_path = os.path.join(output_dir, "clean_shipper.csv")
clean_shipper.to_csv(out_path, index=False)
print(f"Đã xuất: {out_path} ({len(clean_shipper):,} dòng) - Đại diện cho danh sách các tài xế duy nhất")