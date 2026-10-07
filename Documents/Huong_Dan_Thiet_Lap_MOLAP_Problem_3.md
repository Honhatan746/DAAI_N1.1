# HƯỚNG DẪN THIẾT LẬP KHỐI ĐA CHIỀU MOLAP CHO PROBLEM STATEMENT 3
## CHỦ ĐỀ: XÁC ĐỊNH GIAI ĐOẠN TĂNG TRƯỞNG VÀ SUY GIẢM DOANH THU

> **Tài liệu tham chiếu:** [Documents/Problem_Statement_2.md](file:///d:/Project%20DAAI/Documents/Problem_Statement_2.md) (Nội dung phân tích Problem 3)  
> **Cơ sở dữ liệu nguồn:** SQL Server `EcommerceDW`  
> **Mục tiêu:** Hướng dẫn chi tiết từng bước thiết lập khối Time-Intelligence phân tích tăng trưởng MoM, YoY và cảnh báo rủi ro sụt giảm doanh thu.

---

## 1. TỔNG QUAN KIẾN TRÚC KHỐI MOLAP CHO PROBLEM 3

Problem 3 tập trung vào chuỗi thời gian (Time-Series) và phân rã nguyên nhân tăng trưởng:

```
                            ┌──────────────────────────┐
                            │         DIM_DATE         │
                            │ (full_date: 2012 - 2022) │
                            └────────────┬─────────────┘
                                         │ 1
                                         │ order_date_key
                                         ▼ *
┌──────────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────┐
│       DIM_PRODUCT        │   │    FACT_SALES_RETURN     │   │   BRIDGE_ORDER_ITEM_...  │
│  (category > segment)    │◄──┤   (714,669 bản ghi)      ├──►│ (order_item_id, promo_key│
└──────────────────────────┘ 1 *└──────────────────────────┘* 1└────────────┬─────────────┘
      product_key                     order_item_id                          │ *
                                                                             ▼ 1
                                                              ┌──────────────────────────┐
                                                              │      DIM_PROMOTION       │
                                                              │ (promo_name, promo_type) │
                                                              └──────────────────────────┘
```

* **Điểm lưu ý kỹ thuật then chốt:** Bảng `DIM_DATE` bắt buộc phải được đánh dấu là **Date Table** trên cột `full_date` để các hàm Time-Intelligence (`DATEADD`, `SAMEPERIODLASTYEAR`) hoạt động ổn định và chính xác $100\%$.

---

## 2. BƯỚC 1: NẠP THÊM CÁC BẢNG BỔ TRỢ TỪ SQL SERVER (IMPORT TABLES)

Ở Problem 1, chúng ta đã có: `FACT_SALES_RETURN`, `DIM_DATE`, `DIM_PRODUCT`, `DIM_GEOGRAPHY`.  
Để phục vụ phân tích động lực tăng trưởng từ **Chương trình khuyến mãi (Promotion Analysis)** trong Problem 3, bạn nạp thêm 2 bảng từ SQL Server:

1. Trong Power BI Desktop, vào tab **Home** $\longrightarrow$ Chọn **SQL Server** (hoặc **Get Data** $\longrightarrow$ **SQL Server**).
2. Nhập thông tin kết nối máy chủ SQL Server của bạn (Database: `EcommerceDW`, Data Connectivity mode: **Import**).
3. Tại cửa sổ **Navigator**, tích chọn 2 bảng:
   * **`DIM_PROMOTION`** (Danh mục chương trình khuyến mãi)
   * **`BRIDGE_ORDER_ITEM_PROMOTION`** (Bảng cầu nối Nhiều - Nhiều giữa Mặt hàng và Khuyến mãi)
4. Bấm **Load**.

---

## 3. BƯỚC 2: THIẾT LẬP MỐI QUAN HỆ (MODEL RELATIONSHIPS)

Chuyển sang màn hình **Model View** (biểu tượng thứ 3 bên trái giao diện Power BI) để kiểm tra hoặc kéo nối các bảng:

1. **Nối `DIM_PROMOTION` sang `BRIDGE_ORDER_ITEM_PROMOTION`:**
   * Kéo thả: `DIM_PROMOTION[promotion_key]` $\longrightarrow$ `BRIDGE_ORDER_ITEM_PROMOTION[promotion_key]`.
   * **Cardinality:** `One to many (1:*)`.
   * **Cross filter direction:** `Single`.
2. **Nối `BRIDGE_ORDER_ITEM_PROMOTION` sang `FACT_SALES_RETURN`:**
   * Kéo thả: `BRIDGE_ORDER_ITEM_PROMOTION[order_item_id]` $\longrightarrow$ `FACT_SALES_RETURN[order_item_id]`.
   * **Cardinality:** `Many to one (*:1)` (hoặc `1:*` tùy hướng kéo).
   * **Cross filter direction:** Chọn **Both** (Để khi người dùng chọn lọc một chương trình khuyến mãi trên Dashboard, bộ lọc sẽ truyền qua bảng Bridge để lọc trực tiếp doanh thu của `FACT_SALES_RETURN`).

---

## 4. BƯỚC 3: ĐÁNH DẤU DATE TABLE TRÊN `DIM_DATE` (BẮT BUỘC)

1. Trong giao diện Power BI Desktop, tìm bảng `DIM_DATE` ở danh sách bên phải.
2. Bấm chuột phải vào bảng `DIM_DATE` $\longrightarrow$ Chọn **Mark as date table** $\longrightarrow$ **Mark as date table**.
3. Tại ô **Date column**, chọn cột **`full_date`**.
4. Bấm **OK** (Hệ thống sẽ xác nhận: *Validated successfully*).

---

## 5. BƯỚC 4: KỊCH BẢN C# TỰ ĐỘNG HÓA TRONG TABULAR EDITOR (1-CLICK SCRIPT)

Mở **Tabular Editor** (từ tab *External Tools* trên Power BI) $\longrightarrow$ Vào tab **C# Script**, dán toàn bộ đoạn code dưới đây và bấm **F5 (Run)** $\longrightarrow$ bấm **Ctrl + S**:

```csharp
// ============================================================================
// SCRIPT TỰ ĐỘNG TẠO TOÀN BỘ MEASURES CHO PROBLEM 3 (TIME-INTELLIGENCE)
// Tự động: Tạo bảng, sinh Measure, gán Format %, $ và chia thư mục chuẩn hóa
// ============================================================================

// 1. Tạo bảng chứa Measures riêng biệt cho Problem 3
Table p3Table;
if (!Model.Tables.Contains("_Measures_P3")) {
    p3Table = Model.AddTable("_Measures_P3");
} else {
    p3Table = Model.Tables["_Measures_P3"];
}

// 2. Hàm hỗ trợ tạo hoặc cập nhật Measure an toàn (chống lỗi trùng lặp khi chạy lại)
Action<string, string, string, string> AddOrUpdateMeasure = (name, expr, fmt, folder) => {
    Measure m = p3Table.Measures.Contains(name) ? p3Table.Measures[name] : p3Table.AddMeasure(name, expr);
    m.Expression = expr;
    if (!string.IsNullOrEmpty(fmt)) m.FormatString = fmt;
    if (!string.IsNullOrEmpty(folder)) m.DisplayFolder = folder;
};

// ----------------------------------------------------------------------------
// THƯ MỤC 01: PHÂN TÍCH TĂNG TRƯỞNG THEO THÁNG (MoM ANALYSIS)
// ----------------------------------------------------------------------------
AddOrUpdateMeasure(
    "Prior Month Revenue",
    "CALCULATE([Net Revenue], DATEADD(DIM_DATE[full_date], -1, MONTH))",
    "$#,##0.00",
    "01. MoM Analysis"
);

AddOrUpdateMeasure(
    "MoM Growth Value",
    "IF(ISBLANK([Prior Month Revenue]), BLANK(), [Net Revenue] - [Prior Month Revenue])",
    "$#,##0.00",
    "01. MoM Analysis"
);

AddOrUpdateMeasure(
    "MoM Growth %",
    "DIVIDE([MoM Growth Value], [Prior Month Revenue], 0)",
    "0.00%",
    "01. MoM Analysis"
);

// ----------------------------------------------------------------------------
// THƯ MỤC 02: PHÂN TÍCH TĂNG TRƯỞNG CÙNG KỲ (YoY ANALYSIS)
// ----------------------------------------------------------------------------
AddOrUpdateMeasure(
    "Same Period Last Year Revenue",
    "CALCULATE([Net Revenue], SAMEPERIODLASTYEAR(DIM_DATE[full_date]))",
    "$#,##0.00",
    "02. YoY Analysis"
);

AddOrUpdateMeasure(
    "YoY Growth Value",
    "IF(ISBLANK([Same Period Last Year Revenue]), BLANK(), [Net Revenue] - [Same Period Last Year Revenue])",
    "$#,##0.00",
    "02. YoY Analysis"
);

AddOrUpdateMeasure(
    "YoY Growth %",
    "DIVIDE([YoY Growth Value], [Same Period Last Year Revenue], 0)",
    "0.00%",
    "02. YoY Analysis"
);

// ----------------------------------------------------------------------------
// THƯ MỤC 03: PHÂN RÃ ĐỘNG LỰC TĂNG TRƯỞNG (GROWTH DRIVERS)
// ----------------------------------------------------------------------------
AddOrUpdateMeasure(
    "MoM Orders Growth %",
    "VAR PriorOrders = CALCULATE([Total Orders], DATEADD(DIM_DATE[full_date], -1, MONTH)) " +
    "RETURN DIVIDE([Total Orders] - PriorOrders, PriorOrders, 0)",
    "0.00%",
    "03. Growth Drivers"
);

AddOrUpdateMeasure(
    "MoM AOV Growth %",
    "VAR PriorAOV = CALCULATE([Average Order Value], DATEADD(DIM_DATE[full_date], -1, MONTH)) " +
    "RETURN DIVIDE([Average Order Value] - PriorAOV, PriorAOV, 0)",
    "0.00%",
    "03. Growth Drivers"
);

// ----------------------------------------------------------------------------
// THƯ MỤC 04: CẢNH BÁO RỦI RO (RISK ALERTS)
// ----------------------------------------------------------------------------
AddOrUpdateMeasure(
    "Decline Warning Flag",
    "VAR CurrentMoM = [MoM Growth %] " +
    "VAR PrevMoM = CALCULATE([MoM Growth %], DATEADD(DIM_DATE[full_date], -1, MONTH)) " +
    "RETURN IF(ISBLANK(CurrentMoM) || ISBLANK(PrevMoM), \"N/A\", IF(CurrentMoM < 0 && PrevMoM < 0, \"ALERT: 2-MONTH CONSECUTIVE DECLINE\", \"STABLE\"))",
    "",
    "04. Risk Alerts"
);
```

---

## 6. BƯỚC 5: KIỂM THỬ ĐỘ CHÍNH XÁC CỦA PROBLEM 3

Sau khi chạy script và bấm **Ctrl + S**:

1. Mở trang báo cáo mới trong Power BI Desktop (đặt tên trang: `Revenue Growth Dynamics`).
2. Kéo một visual **Matrix Table** vào trang.
3. Kéo cột `DIM_DATE[year]` và `DIM_DATE[month]` vào phần **Rows**.
4. Kéo lần lượt các Measure sau vào phần **Values**:
   * `[Net Revenue]`
   * `[Prior Month Revenue]`
   * `[MoM Growth %]`
   * `[Same Period Last Year Revenue]`
   * `[YoY Growth %]`
   * `[Decline Warning Flag]`
5. **Tiêu chí nghiệm thu:**
   * Tháng $1$ của năm sau đối chiếu đúng với tháng $12$ của năm trước.
   * Cột `MoM Growth %` hiển thị đúng định dạng `%` (có số dương xanh / số âm đỏ).
   * Khi xuất hiện 2 tháng liên tiếp có `MoM Growth % < 0`, cột `Decline Warning Flag` tự động hiện chữ `ALERT: 2-MONTH CONSECUTIVE DECLINE`.
