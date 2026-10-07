# ĐẶC TẢ CHI TIẾT 2 PROBLEM STATEMENTS CHO MÔ HÌNH MOLAP & POWER BI

> **Căn cứ tài liệu:** 
> - [Documents/Requirement build detail Problem statement.md](file:///d:/Project%20DAAI/Documents/Requirement%20build%20detail%20Problem%20statement.md)
> - [Documents/Problem statements.md](file:///d:/Project%20DAAI/Documents/Problem%20statements.md)
> - Kho dữ liệu Star Schema hiện hữu (`EcommerceDW`)
>
> **Mục tiêu:** Định nghĩa kiến trúc khối đa chiều (MOLAP Cube), công thức đo lường DAX, thiết kế trực quan hóa và phương pháp luận trình bày Dashboard theo chuẩn:  
> **Nhìn vào dashboard $\longrightarrow$ Mô tả dữ liệu $\longrightarrow$ Tại sao nó như vậy $\longrightarrow$ Kết luận hành động.**

---

## I. PROBLEM STATEMENT 1: TÍNH TỔNG DOANH THU THỰC TẾ (SAU CHIẾT KHẤU) & ĐÁNH GIÁ DÒNG LỢI NHUẬN

### 1. Ý nghĩa & Mục tiêu kinh doanh
* **Mục tiêu:** Đánh giá dòng tiền lời thực thu của doanh nghiệp sau khi khấu trừ chiết khấu (Discount) và giá vốn (COGS), từ đó nhận diện xem doanh nghiệp đang tăng trưởng thực chất (về lợi nhuận) hay chỉ đang "tăng trưởng ảo" nhờ đốt tiền vào khuyến mãi.
* **Quy mô triển khai:** Tập trung vào nhóm chiều phân tích cốt lõi: **Thời gian (Date)**, **Ngành hàng / Sản phẩm (Product)**, và **Khu vực địa lý (Geography)**.

---

### 2. Các bảng & Cột tham gia xây dựng Measure (Data Inputs)

| Phân Loại Bảng | Tên Bảng | Cột Dữ Liệu Tham Gia | Ý Nghĩa Trong Độ Đo / Chiều Phân Tích |
| :--- | :--- | :--- | :--- |
| **Fact Table** | `FACT_SALES_RETURN` | `quantity`<br>`unit_price`<br>`gross_amount`<br>`discount_amount`<br>`net_amount`<br>`estimated_cost`<br>`estimated_profit`<br>`order_id` | • Số lượng bán<br>• Đơn giá niêm yết<br>• Doanh thu gộp ($quantity \times unit\_price$)<br>• Tổng tiền giảm giá / chiết khấu<br>• Doanh thu thuần ($gross - discount$)<br>• Giá vốn ước tính ($quantity \times cogs$)<br>• Lợi nhuận gộp ($net - cost$)<br>• Đếm đơn hàng duy nhất |
| **Dimension** | `DIM_DATE` | `date_key`<br>`full_date`<br>`year`<br>`quarter`<br>`month`<br>`month_name` | Trục thời gian phân tích doanh thu và lợi nhuận theo năm, quý, tháng. |
| **Dimension** | `DIM_PRODUCT` | `product_key`<br>`category`<br>`segment`<br>`product_name` | Chiều sản phẩm để phân loại ngành hàng nào đóng góp dòng tiền lớn nhất. |
| **Dimension** | `DIM_GEOGRAPHY` | `geography_key`<br>`region`<br>`city` | Chiều địa lý để đánh giá hiệu quả kinh doanh theo vùng miền. |

---

### 3. Danh mục Metrics & KPIs (DAX Measures)

```dax
// 1. Base Measure: Doanh thu gộp
Gross Revenue = SUM(FACT_SALES_RETURN[gross_amount])

// 2. Base Measure: Tổng tiền chiết khấu
Total Discount = SUM(FACT_SALES_RETURN[discount_amount])

// 3. Metric: Doanh thu thuần thực tế (Sau chiết khấu)
Net Revenue = SUM(FACT_SALES_RETURN[net_amount])

// 4. Base Measure: Tổng giá vốn hàng bán
Estimated Cost = SUM(FACT_SALES_RETURN[estimated_cost])

// 5. Metric: Lợi nhuận gộp thực tế
Gross Profit = [Net Revenue] - [Estimated Cost]

// 6. KPI: Tỷ suất lợi nhuận gộp (%)
Profit Margin % = DIVIDE([Gross Profit], [Net Revenue], 0)

// 7. Metric: Tỷ lệ chiết khấu trên doanh thu (%)
Discount Rate % = DIVIDE([Total Discount], [Gross Revenue], 0)

// 8. Metric: Giá trị đơn hàng trung bình (AOV)
Average Order Value (AOV) = DIVIDE([Net Revenue], DISTINCTCOUNT(FACT_SALES_RETURN[order_id]), 0)
```

---

### 4. Thiết kế Dashboard 1: "Net Revenue & Profitability Performance"

#### Bố cục giao diện (16:9):
* **Slicers (Bộ lọc):** `Year` (Năm), `Quarter` (Quý), `Category` (Ngành hàng), `Region` (Vùng miền).
* **Hàng 1 (4 Thẻ KPI chủ lực):**
  1. `[Net Revenue]` (Doanh thu thuần)
  2. `[Total Discount]` (Tổng tiền giảm giá)
  3. `[Gross Profit]` (Lợi nhuận gộp)
  4. `[Profit Margin %]` (Tỷ suất lợi nhuận - định dạng %)
* **Hàng 2 (Trực quan hóa xu hướng & Cơ cấu):**
  * **Biểu đồ Cột kết hợp Đường (Combo Chart):**  
    - Trục X: `DIM_DATE[year > month]`  
    - Cột (Columns): `[Net Revenue]`  
    - Đường (Line): `[Profit Margin %]`
  * **Biểu đồ Cột ngang phân tầng (Clustered Bar Chart):**  
    - Trục Y: `DIM_PRODUCT[category]`  
    - Thanh đo: `[Net Revenue]` và `[Gross Profit]`
* **Hàng 3 (Bảng ma trận chi tiết - Matrix Table):**  
  - Hàng: `DIM_PRODUCT[category] > segment`  
  - Cột giá trị: `[Gross Revenue]`, `[Discount Rate %]`, `[Net Revenue]`, `[Gross Profit]`, `[Profit Margin %]`

---

### 5. Kịch bản Trình bày Case Nghiên cứu Đại diện (Storytelling Framework)

* **Case đại diện:** Phân tích ảnh hưởng của đợt khuyến mãi Q4 ngành hàng *Streetwear*.
* **Các bước trình bày:**
  1. **Nhìn vào Dashboard:**  
     *"Tại biểu đồ Combo Chart, trong Tháng 11 và Tháng 12, cột Net Revenue đạt đỉnh cao nhất năm (tăng vọt lên hơn 1.2 triệu USD), nhưng đường Profit Margin % lại dốc ngược xuống đáy (rơi từ 34% xuống chỉ còn 16%)."*
  2. **Mô tả dữ liệu:**  
     *"Bảng Matrix cho thấy tại ngành hàng Streetwear, Gross Revenue tăng gấp đôi nhưng Discount Rate % bị đẩy lên mức kỷ lục 42% (do chính sách giảm giá Black Friday / Tết). Doanh thu thuần đạt cao nhưng tiền chiết khấu chiếm tới gần một nửa giá trị niêm yết."*
  3. **Tại sao nó như vậy? (Root Cause):**  
     *"Doanh nghiệp áp dụng chính sách giảm giá đại trà (Deep Discount) trên diện rộng để chạy chỉ tiêu doanh số cuối năm. Mặt hàng bán ra số lượng lớn nhưng biên lợi nhuận trên mỗi đơn hàng bị co hẹp nghiêm trọng sau khi trừ giá vốn."*
  4. **Kết luận & Hành động:**  
     *"Doanh nghiệp tăng trưởng về quy mô giao dịch (Scale/Volume) nhưng dòng tiền lời bị xói mòn. Chiến lược quý tới: Bắt buộc áp trần chiết khấu (Discount Cap) tối đa 20% cho nhóm sản phẩm chủ lực và chỉ giảm giá sâu với hàng tồn kho quá 90 ngày."*

---

## II. PROBLEM STATEMENT 2: XÁC ĐỊNH GIAI ĐOẠN TĂNG TRƯỞNG & SUY GIẢM DOANH THU

### 1. Ý nghĩa & Mục tiêu kinh doanh
* **Mục tiêu:** Đo lường động thái tăng trưởng theo tháng (Month-over-Month - MoM) và cùng kỳ năm trước (Year-over-Year - YoY), phát hiện sớm các giai đoạn sụt giảm liên tiếp để kích hoạt cảnh báo rủi ro kinh doanh.
* **Quy mô triển khai:** Khai thác các hàm **Time-Intelligence** của khối MOLAP kết hợp phân rã theo **Số lượng đơn (Order Count)** và **Chương trình khuyến mãi (Promotion)**.

---

### 2. Các bảng & Cột tham gia xây dựng Measure (Data Inputs)

| Phân Loại Bảng | Tên Bảng | Cột Dữ Liệu Tham Gia | Ý Nghĩa Trong Độ Đo / Chiều Phân Tích |
| :--- | :--- | :--- | :--- |
| **Fact Table** | `FACT_SALES_RETURN` | `order_date_key`<br>`net_amount`<br>`order_id`<br>`quantity`<br>`order_item_id` | Khóa liên kết ngày, doanh thu thuần, mã đơn hàng để tính biến động giao dịch. |
| **Dimension** | `DIM_DATE` | `date_key`<br>`full_date`<br>`year`<br>`month`<br>`month_name`<br>`quarter` | Nền tảng cho toàn bộ các phép tính Time-Intelligence trong DAX. |
| **Dimension** | `DIM_PRODUCT` | `product_key`<br>`category` | Phân tích cơ cấu sản phẩm nào kéo tụt hoặc nâng đỡ tăng trưởng. |
| **Bridge & Dim** | `BRIDGE_ORDER_ITEM_PROMOTION`<br>`DIM_PROMOTION` | `promo_id`<br>`promo_name`<br>`promo_type` | Kiểm tra sự tăng trưởng/suy giảm có gắn liền với đợt chạy chiến dịch marketing không. |

---

### 3. Danh mục Metrics & KPIs (Time-Intelligence DAX)

```dax
// 1. Doanh thu tháng hiện tại
Current Month Revenue = [Net Revenue]

// 2. Doanh thu tháng liền trước (Prior Month)
Prior Month Revenue = 
CALCULATE(
    [Net Revenue],
    DATEADD(DIM_DATE[full_date], -1, MONTH)
)

// 3. Giá trị chênh lệch tăng/giảm tháng (MoM Growth Value)
MoM Growth Value = 
IF(
    ISBLANK([Prior Month Revenue]),
    BLANK(),
    [Net Revenue] - [Prior Month Revenue]
)

// 4. KPI Tốc độ tăng trưởng tháng (% MoM Growth)
MoM Growth % = 
DIVIDE([MoM Growth Value], [Prior Month Revenue], 0)

// 5. Doanh thu cùng kỳ năm trước (Same Period Last Year - YoY)
Same Period Last Year Revenue = 
CALCULATE(
    [Net Revenue],
    SAMEPERIODLASTYEAR(DIM_DATE[full_date])
)

// 6. KPI Tăng trưởng cùng kỳ (% YoY Growth)
YoY Growth % = 
DIVIDE([Net Revenue] - [Same Period Last Year Revenue], [Same Period Last Year Revenue], 0)

// 7. Cờ cảnh báo suy giảm liên tiếp (Decline Alert: 1 nếu tháng này và tháng trước đều âm)
Decline Warning Flag = 
VAR CurrentMoM = [MoM Growth %]
VAR PrevMoM = 
    CALCULATE(
        [MoM Growth %],
        DATEADD(DIM_DATE[full_date], -1, MONTH)
    )
RETURN
    IF(CurrentMoM < 0 && PrevMoM < 0, "CẢNH BÁO: SUY GIẢM 2 THÁNG LIÊN TIẾP", "BÌNH THƯỜNG")
```

---

### 4. Thiết kế Dashboard 2: "Revenue Growth & Decline Dynamics"

#### Bố cục giao diện (16:9):
* **Slicers (Bộ lọc):** `Year` (Năm phân tích), `Region` (Vùng miền), `Promotion Channel` (Kênh khuyến mãi).
* **Hàng 1 (4 Thẻ KPI động lực):**
  1. `[Current Month Revenue]` (Doanh thu tháng đang chọn)
  2. `[MoM Growth %]` (Tăng trưởng so với tháng trước - có icon xanh/đỏ)
  3. `[YoY Growth %]` (Tăng trưởng so với cùng kỳ năm trước)
  4. `[Decline Warning Flag]` (Thẻ trạng thái cảnh báo sớm)
* **Hàng 2 (Phân tích biến động & Thác nước):**
  * **Biểu đồ Thác nước (Waterfall Chart):**  
    - Phân tích đóng góp tăng/giảm doanh thu MoM: từ Doanh thu tháng trước $\rightarrow$ Tăng/giảm từng Category $\rightarrow$ Doanh thu tháng này.
  * **Biểu đồ Đường so sánh đa năm (Multi-Year Seasonality Line Chart):**  
    - Trục X: Tháng (1 đến 12)  
    - Đường 1: Năm hiện tại (2022)  
    - Đường 2: Năm trước (2021)  
    - Đường 3: Năm trước nữa (2020)
* **Hàng 3 (Phân tích nguyên nhân suy giảm - Breakdown Tree / Decomposition Tree):**  
  - Nút gốc: `[MoM Growth Value]`  
  - Nhánh phân rã cấp 1: Biến động do `Total Orders` (Số lượng đơn) hay do `Average Order Value` (Giá trị đơn).  
  - Nhánh phân rã cấp 2: Phân rã theo `DIM_PRODUCT[category]`.

---

### 5. Kịch bản Trình bày Case Nghiên cứu Đại diện (Storytelling Framework)

* **Case đại diện:** Phân tích giai đoạn suy giảm doanh thu đầu năm (Tháng 1 & Tháng 2).
* **Các bước trình bày:**
  1. **Nhìn vào Dashboard:**  
     *"Tại thẻ KPI, thẻ Cảnh báo chuyển sang màu đỏ: 'CẢNH BÁO: SUY GIẢM 2 THÁNG LIÊN TIẾP'. Biểu đồ MoM Growth % hiển thị Tháng 1 giảm -18.5% và Tháng 2 tiếp tục giảm -12.3%."*
  2. **Mô tả dữ liệu:**  
     *"Tại biểu đồ Decomposition Tree, khi phân rã mức sụt giảm doanh thu 150,000 USD trong Tháng 2: số lượng đơn hàng (Total Orders) bị tụt giảm tới 28%, trong khi giá trị đơn trung bình (AOV) vẫn giữ nguyên ở mức 52 USD/đơn."*
  3. **Tại sao nó như vậy? (Root Cause):**  
     *"Sau đợt kích cầu ồ ạt dịp Tết và Q4, khách hàng đã hoàn tất nhu cầu mua sắm. Đồng thời, tệp khuyến mãi (Promotion) cho thấy các chương trình Marketing kết thúc vào cuối tháng 1 mà không có chiến dịch gối đầu trong tháng 2. Khách hàng không quay lại mua sắm (Retention suy giảm)."*
  4. **Kết luận & Hành động:**  
     *"Đây là hiện tượng suy giảm mang tính mùa vụ (Seasonality Dip) kết hợp với khoảng trống khuyến mãi. Hành động đề xuất: Thay vì chi tiền tìm kiếm khách hàng mới tốn kém trong giai đoạn thấp điểm, bộ phận kinh doanh cần triển khai chiến dịch Chăm sóc khách hàng cũ (Re-engagement campaign) kèm mã ưu đãi kích cầu cho các khách hàng đã mua trong Q4."*

---

## III. TỔNG KẾT SO SÁNH GIỮA 2 DASHBOARD

| Tiêu Chí | Dashboard 1: Net Revenue & Profitability | Dashboard 2: Growth & Decline Dynamics |
| :--- | :--- | :--- |
| **Trọng tâm quản trị** | Chất lượng dòng tiền (Sức khỏe lợi nhuận) | Động lực và Tốc độ phát triển (Tăng trưởng quy mô) |
| **Câu hỏi then chốt** | *"Doanh nghiệp bán được nhiều hàng, nhưng thực sự bỏ túi được bao nhiêu tiền lời?"* | *"Doanh thu đang tăng hay đang giảm? Tăng/giảm do đâu (số lượng đơn hay giá trị đơn)?"* |
| **Kỹ thuật DAX cốt lõi** | Phép tính số học đa cột: Gross, Discount, Net, COGS, Profit Margin | Phép tính Time-Intelligence: `DATEADD`, `SAMEPERIODLASTYEAR`, `IF(Condition)` |
| **Công cụ trực quan hóa chính** | Combo Chart, Matrix Table, Scatter Plot | Waterfall Chart, Decomposition Tree, Seasonality Line Chart |
