import json
import os
import re
import numpy as np
import pandas as pd


def extract_id_series(series):
  """Trích xuất số nguyên an toàn bằng regex"""
  s_str = series.astype(str).str.strip()
  extracted = s_str.str.extract(r'(\d+)', expand=False)
  return pd.to_numeric(extracted, errors='coerce')


def build_order_item_promotion(
    bridge_source_path='/content/export/clean_order_item_promotion.csv', # New parameter for the bridge table itself
    order_item_ref_path='/content/export/clean_order_item.csv', # Changed name for clarity
    promotion_ref_path='/content/clean_promotion.csv', # Changed name for clarity
):

  print('=== BẮT ĐẦU LÀM SẠCH VÀ KIỂM TRA BẢNG CẦU NỐI ORDER_ITEM_PROMOTION ===')

  # 1. LOAD KHÓA NGOẠI THAM CHIẾU (PARENT KEYS)
  # --- Valid order_item_ids ---
  try:
    df_items_ref = pd.read_csv(order_item_ref_path, low_memory=False)
    df_items_ref.columns = df_items_ref.columns.str.strip().str.lower()

    item_id_col_ref = next(
        (c for c in df_items_ref.columns if 'order_item_id' in c or c == 'id'),
        None,
    )
    if not item_id_col_ref:
        print(f"Error: Column 'order_item_id' not found in {order_item_ref_path}.")
        return pd.DataFrame()

    valid_order_item_ids = set(
        extract_id_series(df_items_ref[item_id_col_ref]).dropna().astype(int)
    )
    print(f'-> Số lượng order_item_id hợp lệ từ {order_item_ref_path}: {len(valid_order_item_ids)}')
  except FileNotFoundError:
      print(f"Error: {order_item_ref_path} not found. Cannot validate order_item_id.")
      valid_order_item_ids = set()
  except Exception as e:
      print(f"Error loading {order_item_ref_path}: {e}")
      valid_order_item_ids = set()

  # --- Valid promo_ids ---
  try:
    df_promos_ref = pd.read_csv(promotion_ref_path, low_memory=False)
    df_promos_ref.columns = df_promos_ref.columns.str.strip().str.lower()
    promo_id_col_ref = next(
        (c for c in df_promos_ref.columns if 'promo_id' in c), None
    )
    if not promo_id_col_ref:
        print(f"Error: Column 'promo_id' not found in {promotion_ref_path}.")
        return pd.DataFrame()
    valid_promo_ids = set(
        extract_id_series(df_promos_ref[promo_id_col_ref]).dropna().astype(int)
    )
    print(f'-> Số lượng promo_id hợp lệ từ {promotion_ref_path}: {len(valid_promo_ids)}')
  except FileNotFoundError:
      print(f"Error: {promotion_ref_path} not found. Cannot validate promo_id.")
      valid_promo_ids = set()
  except Exception as e:
      print(f"Error loading {promotion_ref_path}: {e}")
      valid_promo_ids = set()

  if not valid_order_item_ids or not valid_promo_ids:
      print("[CẢNH BÁO] Không thể tiến hành kiểm tra FK do thiếu dữ liệu tham chiếu.")
      # In this case, we might still process the bridge table but without full FK validation
      # Or return empty if FK validation is critical
      # For now, let's allow partial processing if validation data is missing, but log a warning.

  # 2. LOAD BẢNG CẦU NỐI (BRIDGE TABLE)
  print(f"\n--- Đang tải dữ liệu cầu nối từ: {bridge_source_path} ---")
  try:
    df_bridge = pd.read_csv(bridge_source_path, low_memory=False)
    df_bridge.columns = df_bridge.columns.str.strip().str.lower()
    print(f"Số bản ghi ban đầu từ {bridge_source_path}: {len(df_bridge)}")
  except FileNotFoundError:
    print(f"Error: {bridge_source_path} not found. Please ensure the file is uploaded or generated.")
    return pd.DataFrame(columns=['order_item_id', 'promo_id'])
  except Exception as e:
    print(f"Error loading bridge table from {bridge_source_path}: {e}")
    return pd.DataFrame(columns=['order_item_id', 'promo_id'])

  if df_bridge.empty:
    print("[CẢNH BÁO] Bảng cầu nối rỗng, không có dữ liệu để xử lý.")
    return pd.DataFrame(columns=['order_item_id', 'promo_id'])

  initial_records = len(df_bridge)

  # 3. TIỀN XỬ LÝ & LÀM SẠCH KIỂU DỮ LIỆU
  print('\n--- Tiền xử lý dữ liệu cầu nối ---')
  if 'order_item_id' not in df_bridge.columns or 'promo_id' not in df_bridge.columns:
    print("CRITICAL ERROR: 'order_item_id' or 'promo_id' columns not found in bridge table source.")
    return pd.DataFrame(columns=['order_item_id', 'promo_id'])

  df_bridge['order_item_id'] = extract_id_series(df_bridge['order_item_id'])
  df_bridge['promo_id'] = extract_id_series(df_bridge['promo_id'])

  # Xóa null và ép int
  df_bridge = df_bridge.dropna(subset=['order_item_id', 'promo_id']).copy()
  df_bridge['order_item_id'] = df_bridge['order_item_id'].astype(int)
  df_bridge['promo_id'] = df_bridge['promo_id'].astype(int)

  # Drop duplicate trên Composite PK (order_item_id, promo_id)
  rows_before_dedup = len(df_bridge)
  df_bridge = df_bridge.drop_duplicates(subset=['order_item_id', 'promo_id'])
  duplicates_dropped = rows_before_dedup - len(df_bridge)
  if duplicates_dropped > 0:
      print(f'-> Đã loại bỏ {duplicates_dropped} bản ghi trùng lặp trên PK (order_item_id, promo_id).')
  print(f'Số bản ghi sau khi lọc null và trùng lặp PK: {len(df_bridge)}')

  # 4. KIỂM TRA TOÀN VẸN KHÓA NGOẠI (DUAL FK CHECK)
  print('\n--- Đối chiếu Khóa Ngoại ---')
  if not df_bridge.empty and valid_order_item_ids and valid_promo_ids:
    mask_item = df_bridge['order_item_id'].isin(valid_order_item_ids)
    mask_promo = df_bridge['promo_id'].isin(valid_promo_ids)

    orphan_items = (~mask_item).sum()
    orphan_promos = (~mask_promo).sum()

    if orphan_items > 0:
      print(
          f'  - Loại bỏ {orphan_items} dòng do order_item_id không có trong {order_item_ref_path}'
      )
    if orphan_promos > 0:
      print(
          f'  - Loại bỏ {orphan_promos} dòng do promo_id không có trong {promotion_ref_path}'
      )

    df_clean = df_bridge[mask_item & mask_promo].copy()
    fk_dropped = len(df_bridge) - len(df_clean)
    if fk_dropped > 0:
        print(f"-> Tổng số dòng bị loại bỏ do FK mồ côi: {fk_dropped}.")
  elif not df_bridge.empty:
      df_clean = df_bridge.copy() # No FK validation if reference data is missing
      print("-> Bỏ qua kiểm tra FK do thiếu dữ liệu tham chiếu hoặc bảng cầu nối rỗng.")
  else:
      df_clean = pd.DataFrame(columns=['order_item_id', 'promo_id'])


  # 5. XUẤT FILE CSV
  output_file = '/content/clean_order_item_promotion.csv'
  df_clean.to_csv(output_file, index=False)

  print('\n' + '=' * 50)
  print(f'TỔNG KẾT BẢNG ORDER_ITEM_PROMOTION:')
  print(f'- Bản ghi ban đầu (trước xử lý): {initial_records}')
  print(f'- Bản ghi hợp lệ cuối cùng: {len(df_clean)}')
  print(f'- Đã lưu tại: {output_file}')
  print('=' * 50)

  return df_clean


if __name__ == '__main__':
    # Thực thi pipeline
    cleaned_bridge_df = build_order_item_promotion()
    if not cleaned_bridge_df.empty:
        print("\nCleaned DataFrame head:")
        print(cleaned_bridge_df.head().to_markdown(index=False))