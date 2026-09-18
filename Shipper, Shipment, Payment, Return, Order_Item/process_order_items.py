import pandas as pd
import os

output_dir = "export"
os.makedirs(output_dir, exist_ok=True)

print("--- XỬ LÝ ORDER_ITEM & PROMOTION ---")

# 1. Toàn vẹn tham chiếu
df_orders = pd.read_csv("orders_enriched.csv", low_memory=False)
valid_order_ids = set(df_orders['order_id'].astype(int))

df_oi = pd.read_csv("order_items.csv", low_memory=False)
df_oi = df_oi[df_oi['order_id'].isin(valid_order_ids)]

# Tạo khóa nhân tạo order_item_id để định danh từng dòng sản phẩm
df_oi.insert(0, 'order_item_id', range(1, len(df_oi) + 1))

# 2. Xử lý tách bảng ORDER_ITEM
oi_cols = ['order_item_id', 'order_id', 'product_id', 'quantity', 'unit_price', 'discount_amount']
clean_order_item = df_oi[oi_cols].copy()

# Làm sạch dữ liệu (Data Cleansing): Không chấp nhận số lượng và đơn giá âm
clean_order_item['quantity'] = clean_order_item['quantity'].apply(lambda x: x if pd.notnull(x) and x > 0 else 1)
clean_order_item['unit_price'] = clean_order_item['unit_price'].apply(lambda x: x if pd.notnull(x) and x >= 0 else 0)

out_oi = os.path.join(output_dir, "clean_order_item.csv")
clean_order_item.to_csv(out_oi, index=False)
print(f"Đã xuất Bảng Order Item: {out_oi} ({len(clean_order_item):,} dòng)")

# 3. Xử lý vi phạm 1NF: Bảng trung gian ORDER_ITEM_PROMOTION
# Chuyển đổi 2 cột promo_id và promo_id_2 thành các dòng độc lập tương ứng với order_item_id
promo1 = df_oi[['order_item_id', 'promo_id']].dropna().rename(columns={'promo_id': 'promo_id_val'})
promo2 = df_oi[['order_item_id', 'promo_id_2']].dropna().rename(columns={'promo_id_2': 'promo_id_val'})

# Gộp lại và xóa trùng lặp (tránh trường hợp promo_id_1 == promo_id_2)
clean_oi_promo = pd.concat([promo1, promo2]).drop_duplicates().rename(columns={'promo_id_val': 'promo_id'})

out_promo = os.path.join(output_dir, "clean_order_item_promotion.csv")
clean_oi_promo.to_csv(out_promo, index=False)
print(f"Đã xuất Bảng Cầu nối (Bridge table): {out_promo} ({len(clean_oi_promo):,} dòng)")