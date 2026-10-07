# HƯỚNG DẪN THIẾT LẬP KHỐI ĐA CHIỀU MOLAP CHO PROBLEM STATEMENT 1
## CHỦ ĐỀ: TÍNH TỔNG DOANH THU THỰC TẾ & ĐÁNH GIÁ DÒNG LỢI NHUẬN

> **Tài liệu tham chiếu:** [Documents/Problem_Statement_1.md](file:///d:/Project%20DAAI/Documents/Problem_Statement_1.md)  
> **Cơ sở dữ liệu nguồn:** SQL Server `EcommerceDW`  
> **Mục tiêu:** Hướng dẫn chi tiết từng bước xây dựng khối dữ liệu đa chiều (MOLAP / Tabular Model) từ kết nối dữ liệu, thiết lập quan hệ, cấu hình phân cấp chiều (Hierarchies) đến tạo độ đo DAX chuẩn hóa.

---

## 1. TỔNG QUAN KIẾN TRÚC KHỐI MOLAP CHO PROBLEM 1

Khối MOLAP của Problem 1 được triển khai theo mô hình **Star Schema tinh gọn (Modular Scope)**, gồm 1 bảng Fact trung tâm và 3 bảng Dimension bao quanh:

```
                  ┌──────────────────────┐
                  │       DIM_DATE       │
                  │ (Năm > Quý > Tháng)  │
                  └──────────┬───────────┘
                             │ 1
                             │ order_date_key
                             ▼ *
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│     DIM_PRODUCT      │   │  FACT_SALES_RETURN   │   │    DIM_GEOGRAPHY     │
│(Category > Segment)  │◄──┤  (714,669 bản ghi)   ├──►│    (Region > City)   │
└──────────────────────┘ 1 *└──────────────────────┘* 1└──────────────────────┘
      product_key                                        geography_key
```

* **Chế độ lưu trữ khuyến nghị:** **Import (In-Memory / VertiPaq Engine)** để đạt tốc độ nén dữ liệu và phản hồi truy vấn tính toán lợi nhuận nhanh nhất.

---

## 2. BƯỚC 1: KẾT NỐI NGUỒN DỮ LIỆU & IMPORT BẢNG

Trong môi trường làm việc (**Power BI Desktop** hoặc **Visual Studio / Tabular Editor**):

1. Chọn **Get Data** $\longrightarrow$ **SQL Server Database**.
2. Thiết lập thông số kết nối:
   * **Server:** `localhost`
   * **Database:** `EcommerceDW`
   * **Data Connectivity mode:** Chọn **Import**.
3. Tại cửa sổ **Navigator**, tích chọn chính xác **4 bảng** tham gia Problem 1:
   * ✔ `dbo.FACT_SALES_RETURN`
   * ✔ `dbo.DIM_DATE`
   * ✔ `dbo.DIM_PRODUCT`
   * ✔ `dbo.DIM_GEOGRAPHY`
4. Bấm **Load** để nạp dữ liệu vào khối In-Memory.

---

## 3. BƯỚC 2: THIẾT LẬP MỐI QUAN HỆ KHỐI ĐA CHIỀU (RELATIONSHIPS)

Chuyển sang giao diện **Model View**, kiểm tra và thiết lập 3 đường quan hệ sau (Đảm bảo lọc $1$ chiều từ Dim sang Fact):

| Bảng Gốc (Primary / 1) | Cột Khóa (PK) | Bảng Đích (Foreign / *) | Cột Khóa Ngoại (FK) | Cardinality | Trạng Thái |
| :--- | :--- | :--- | :--- | :---: | :---: |
| `dbo.DIM_DATE` | `date_key` | `dbo.FACT_SALES_RETURN` | `order_date_key` | $1 : \text{Many}$ | **Active** |
| `dbo.DIM_PRODUCT` | `product_key` | `dbo.FACT_SALES_RETURN` | `product_key` | $1 : \text{Many}$ | **Active** |
| `dbo.DIM_GEOGRAPHY` | `geography_key` | `dbo.FACT_SALES_RETURN` | `geography_key` | $1 : \text{Many}$ | **Active** |

> **Lưu ý kỹ thuật:** Chiều lọc (Cross filter direction) bắt buộc để **Single** (Dimension lọc Fact). Ẩn các cột khóa kỹ thuật (`order_date_key`, `product_key`, `geography_key`) trên bảng Fact để người dùng không kéo nhầm vào báo cáo.

---

## 4. BƯỚC 3: THIẾT LẬP THUỘC TÍNH CHIỀU & PHÂN CẤP (HIERARCHIES)

Để hỗ trợ thao tác khoan sâu (Drill-down) từ tổng quan xuống chi tiết trên MOLAP Cube:

### 4.1. Phân cấp Thời gian (Date Hierarchy) trên `DIM_DATE`
1. Chuột phải vào cột `year` $\longrightarrow$ Chọn **Create hierarchy** $\longrightarrow$ Đặt tên: `Date Hierarchy`.
2. Lần lượt kéo các cột sau vào phân cấp:
   * `year` (Năm)
   * `quarter` (Quý)
   * `month_name` (Tháng)
   * `full_date` (Ngày)
3. **Sắp xếp tháng theo thứ tự thời gian (Bắt buộc):**  
   Chọn cột `month_name` $\longrightarrow$ Vào tab **Column tools** $\longrightarrow$ Chọn **Sort by column** $\longrightarrow$ Chọn cột **`month`** (để tháng hiển thị đúng từ tháng 1 đến tháng 12 thay vì theo bảng chữ cái A-Z).

### 4.2. Phân cấp Sản phẩm (Product Hierarchy) trên `DIM_PRODUCT`
1. Chuột phải vào cột `category` $\longrightarrow$ **Create hierarchy** $\longrightarrow$ Đặt tên: `Product Hierarchy`.
2. Kéo thêm các cấp:
   * `category` (Ngành hàng)
   * `segment` (Phân khúc)
   * `product_name` (Tên sản phẩm)

### 4.3. Phân cấp Địa lý (Geography Hierarchy) trên `DIM_GEOGRAPHY`
1. Chuột phải vào cột `region` $\longrightarrow$ **Create hierarchy** $\longrightarrow$ Đặt tên: `Geography Hierarchy`.
2. Kéo thêm cấp:
   * `region` (Vùng miền)
   * `city` (Tỉnh / Thành phố)

---

## 5. BƯỚC 4: THIẾT LẬP TẦNG ĐỘ ĐO NGỮ NGHĨA (DAX MEASURES)

Tạo một bảng riêng để quản lý các Measures: Vào tab **Home** $\longrightarrow$ **Enter Data** $\longrightarrow$ Đặt tên bảng là **`_Measures_P1`**.

Lần lượt tạo các độ đo theo 3 nhóm thư mục (Display Folders):

### Thư mục: `01. Revenue & Discount` (Doanh thu & Chiết khấu)

```dax
// Doanh thu gộp ban đầu
Gross Revenue = SUM(FACT_SALES_RETURN[gross_amount])

// Tổng tiền giảm giá / chiết khấu
Total Discount = SUM(FACT_SALES_RETURN[discount_amount])

// Doanh thu thuần thực tế (Sau chiết khấu)
Net Revenue = SUM(FACT_SALES_RETURN[net_amount])

// Tỷ lệ chiết khấu trên doanh thu gộp
Discount Rate % = 
DIVIDE([Total Discount], [Gross Revenue], 0)
```
*Định dạng:* `Gross Revenue`, `Total Discount`, `Net Revenue` chọn định dạng **Currency ($)** hoặc **Decimal Number**. `Discount Rate %` chọn định dạng **Percentage (%)** với 2 chữ số thập phân.

---

### Thư mục: `02. Cost & Profitability` (Giá vốn & Lợi nhuận)

```dax
// Tổng giá vốn hàng bán
Estimated Cost = SUM(FACT_SALES_RETURN[estimated_cost])

// Dòng tiền lời gộp thực tế
Gross Profit = [Net Revenue] - [Estimated Cost]

// Tỷ suất lợi nhuận gộp (%)
Profit Margin % = 
DIVIDE([Gross Profit], [Net Revenue], 0)
```
*Định dạng:* `Estimated Cost`, `Gross Profit` định dạng **Currency ($)**. `Profit Margin %` định dạng **Percentage (%)**.

---

### Thư mục: `03. Volume & Operations` (Sản lượng & Đơn hàng)

```dax
// Tổng sản lượng bán
Total Units Sold = SUM(FACT_SALES_RETURN[quantity])

// Tổng số đơn hàng duy nhất
Total Orders = DISTINCTCOUNT(FACT_SALES_RETURN[order_id])

// Giá trị trung bình trên một đơn hàng
Average Order Value = 
DIVIDE([Net Revenue], [Total Orders], 0)
```
*Định dạng:* `Total Units Sold`, `Total Orders` định dạng **Whole Number (,0)**. `Average Order Value` định dạng **Currency ($)**.

---

## 6. BƯỚC 5: KỊCH BẢN TỰ ĐỘNG HÓA 1-CLICK (TABULAR EDITOR C# SCRIPT)

Nếu bạn sử dụng công cụ **Tabular Editor** (miễn phí, nằm trong tab *External Tools* của Power BI), bạn không cần tạo thủ công từng measure trên. 

Chỉ cần mở **Tabular Editor** $\longrightarrow$ Mở tab **C# Script**, dán đoạn code dưới đây và bấm **Run (F5)**:

```csharp
// 1. Tạo bảng chứa Measures nếu chưa có
Table measureTable;
if (!Model.Tables.Contains("_Measures_P1")) {
    measureTable = Model.AddTable("_Measures_P1");
} else {
    measureTable = Model.Tables["_Measures_P1"];
}

// 2. Thêm các Measures kèm định dạng và thư mục hiển thị
var m1 = measureTable.AddMeasure("Gross Revenue", "SUM(FACT_SALES_RETURN[gross_amount])");
m1.FormatString = "$#,##0.00";
m1.DisplayFolder = "01. Revenue & Discount";

var m2 = measureTable.AddMeasure("Total Discount", "SUM(FACT_SALES_RETURN[discount_amount])");
m2.FormatString = "$#,##0.00";
m2.DisplayFolder = "01. Revenue & Discount";

var m3 = measureTable.AddMeasure("Net Revenue", "SUM(FACT_SALES_RETURN[net_amount])");
m3.FormatString = "$#,##0.00";
m3.DisplayFolder = "01. Revenue & Discount";

var m4 = measureTable.AddMeasure("Discount Rate %", "DIVIDE([Total Discount], [Gross Revenue], 0)");
m4.FormatString = "0.00%";
m4.DisplayFolder = "01. Revenue & Discount";

var m5 = measureTable.AddMeasure("Estimated Cost", "SUM(FACT_SALES_RETURN[estimated_cost])");
m5.FormatString = "$#,##0.00";
m5.DisplayFolder = "02. Cost & Profitability";

var m6 = measureTable.AddMeasure("Gross Profit", "[Net Revenue] - [Estimated Cost]");
m6.FormatString = "$#,##0.00";
m6.DisplayFolder = "02. Cost & Profitability";

var m7 = measureTable.AddMeasure("Profit Margin %", "DIVIDE([Gross Profit], [Net Revenue], 0)");
m7.FormatString = "0.00%";
m7.DisplayFolder = "02. Cost & Profitability";

var m8 = measureTable.AddMeasure("Total Units Sold", "SUM(FACT_SALES_RETURN[quantity])");
m8.FormatString = "#,##0";
m8.DisplayFolder = "03. Volume & Operations";

var m9 = measureTable.AddMeasure("Total Orders", "DISTINCTCOUNT(FACT_SALES_RETURN[order_id])");
m9.FormatString = "#,##0";
m9.DisplayFolder = "03. Volume & Operations";

var m10 = measureTable.AddMeasure("Average Order Value", "DIVIDE([Net Revenue], [Total Orders], 0)");
m10.FormatString = "$#,##0.00";
m10.DisplayFolder = "03. Volume & Operations";
```
*Sau khi chạy xong, bấm **Ctrl + S** để lưu mô hình. Toàn bộ độ đo sẽ xuất hiện ngay lập tức trong Power BI!*

---

## 7. BƯỚC 6: KIỂM THỬ KHỐI MOLAP (VALIDATION TEST)

Trước khi tiến hành làm giao diện, thực hiện kiểm thử tính toán của khối MOLAP:

1. Kéo visual **Matrix Table** vào trang trắng.
2. Thả `DIM_PRODUCT[category]` vào phần **Rows**.
3. Thả lần lượt các measures vào phần **Values**:
   * `Gross Revenue`
   * `Total Discount`
   * `Discount Rate %`
   * `Net Revenue`
   * `Gross Profit`
   * `Profit Margin %`
4. **Tiêu chí nghiệm thu:**
   * $Net\ Revenue = Gross\ Revenue - Total\ Discount$.
   * $Gross\ Profit = Net\ Revenue - Estimated\ Cost$.
   * Khi bấm vào dấu `+` của `Category` để khoan xuống `Segment`, số liệu tự động phân bổ chính xác.
