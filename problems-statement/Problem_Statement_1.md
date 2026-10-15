# PROBLEM STATEMENT 1: TÍNH TỔNG DOANH THU THỰC TẾ (SAU CHIẾT KHẤU) & ĐÁNH GIÁ DÒNG LỢI NHUẬN

## 1. Ý NGHĨA & MỤC TIÊU KINH DOANH (BUSINESS OBJECTIVE)

* **Bối cảnh & Vấn đề thực tế:**  
  Trong thương mại điện tử, doanh thu gộp niêm yết (Gross Revenue) thường bị thổi phồng bởi các đợt flash sale, xả hàng hoặc mã giảm giá ồ ạt. Một doanh nghiệp có thể ghi nhận doanh thu tăng trưởng rất cao, nhưng nếu chiết khấu quá sâu thì dòng tiền lời thực tế (Cash Profitability) bị xói mòn nghiêm trọng, dẫn đến tình trạng "bán nhiều nhưng không có lời".
* **Mục tiêu phân tích:**  
  1. Xác định chính xác **Doanh thu thuần thực tế (Net Revenue)** sau khi đã khấu trừ toàn bộ các khoản giảm giá, chiết khấu và hoàn trả.
  2. Đo lường **Dòng tiền lời gộp (Gross Profit)** và **Tỷ suất lợi nhuận (Profit Margin %)** sau khi trừ giá vốn hàng bán (COGS).
  3. Đánh giá chất lượng tăng trưởng: Phân định rõ ngành hàng và phân khúc sản phẩm nào mang lại lợi nhuận thực chất, ngành hàng nào đang chịu chiết khấu quá mức làm hao hụt dòng tiền.
* **Phạm vi triển khai (MOLAP Scope):**  
  Tập trung vào 3 chiều phân tích cốt lõi: **Thời gian (`DIM_DATE`)**, **Sản phẩm / Ngành hàng (`DIM_PRODUCT`)**, và **Địa lý (`DIM_GEOGRAPHY`)**.

---

## 2. CÁC BẢNG & CỘT DỮ LIỆU THAM GIA XÂY DỰNG ĐỘ ĐO (DATA INPUTS)

### 2.1. Bảng Fact chính: `FACT_SALES_RETURN`
Bảng lưu trữ từng dòng mặt hàng bán ra và thông tin hoàn trả tương ứng (Grain: 1 dòng / 1 `order_item_id`).

| Cột Dữ Liệu | Kiểu Dữ Liệu | Vai Trò Trong Xây Dựng Measure / Metric |
| :--- | :--- | :--- |
| `quantity` | `INT` | Số lượng sản phẩm bán ra; dùng để tính tổng sản lượng bán và nhân với giá vốn/đơn giá. |
| `unit_price` | `DECIMAL(19,4)` | Đơn giá niêm yết của sản phẩm tại thời điểm đặt hàng. |
| `gross_amount` | `DECIMAL(19,4)` | Doanh thu gộp ban đầu ($quantity \times unit\_price$). |
| `discount_amount` | `DECIMAL(19,4)` | Tổng giá trị giảm giá/chiết khấu phân bổ cho mặt hàng đó. |
| `net_amount` | `DECIMAL(19,4)` | Doanh thu thuần thực tế sau chiết khấu ($gross\_amount - discount\_amount$). |
| `estimated_cost` | `DECIMAL(19,4)` | Tổng giá vốn hàng bán ước tính ($quantity \times cogs$). |
| `estimated_profit` | `DECIMAL(19,4)` | Tiền lời gộp dự kiến ($net\_amount - estimated\_cost$). |
| `refund_amount` | `DECIMAL(19,4)` | Tổng tiền đã hoàn trả cho khách nếu mặt hàng có phát sinh đổi trả. |
| `order_id` | `VARCHAR(50)` | Khóa đơn hàng; dùng để đếm số đơn hàng duy nhất (`DISTINCTCOUNT`) nhằm tính giá trị trung bình đơn (AOV). |

### 2.2. Các Bảng Dimension tham gia cắt lát (Slicing & Dicing)

| Tên Bảng Dimension | Cột Dữ Liệu Tham Gia | Ý Nghĩa Trong Chiều Phân Tích (Dimensions) |
| :--- | :--- | :--- |
| **`DIM_DATE`** | `date_key`, `full_date`, `year`, `quarter`, `month`, `month_name` | Cắt lát dòng tiền doanh thu và lợi nhuận theo trục thời gian (Năm, Quý, Tháng). |
| **`DIM_PRODUCT`** | `product_key`, `product_id`, `category`, `segment`, `product_name` | Phân nhóm ngành hàng và phân khúc sản phẩm đóng góp dòng tiền lời cao nhất / thấp nhất. |
| **`DIM_GEOGRAPHY`** | `geography_key`, `region`, `city` | Đánh giá hiệu quả kinh doanh và khả năng sinh lời theo từng vùng miền / tỉnh thành. |

---

## 3. DANH MỤC MEASURES, METRICS & KPIS (CÔNG THỨC TOÁN HỌC & DAX)

### 3.1. Base Measures (Độ đo cơ sở)
Các độ đo tích lũy nguyên thủy được tổng hợp trực tiếp từ các cột số lượng và số tiền của bảng Fact:

* **Tổng Doanh thu Gộp (Gross Revenue):**
  $$\text{Gross Revenue} = \sum (\text{gross\_amount})$$
  ```dax
  Gross Revenue = SUM(FACT_SALES_RETURN[gross_amount])
  ```

* **Tổng Tiền Chiết khấu / Giảm giá (Total Discount):**
  $$\text{Total Discount} = \sum (\text{discount\_amount})$$
  ```dax
  Total Discount = SUM(FACT_SALES_RETURN[discount_amount])
  ```

* **Tổng Doanh thu Thuần Thực tế (Net Revenue):**
  $$\text{Net Revenue} = \sum (\text{net\_amount})$$
  ```dax
  Net Revenue = SUM(FACT_SALES_RETURN[net_amount])
  ```

* **Tổng Giá vốn Hàng bán (Total Cost of Goods Sold - COGS):**
  $$\text{Estimated Cost} = \sum (\text{estimated\_cost})$$
  ```dax
  Estimated Cost = SUM(FACT_SALES_RETURN[estimated_cost])
  ```

* **Tổng Số lượng Bán (Total Units Sold):**
  ```dax
  Total Units Sold = SUM(FACT_SALES_RETURN[quantity])
  ```

* **Tổng Số Đơn hàng Duy nhất (Total Orders):**
  ```dax
  Total Orders = DISTINCTCOUNT(FACT_SALES_RETURN[order_id])
  ```

---

### 3.2. Derived Metrics (Chỉ số nghiệp vụ dẫn xuất)
Các chỉ số kinh doanh được suy diễn từ sự kết hợp của nhiều Measures cơ sở để phản ánh khía cạnh tài chính:

* **Lợi nhuận Gộp Thực tế (Gross Profit):**  
  Phản ánh dòng tiền lời thực sự còn giữ lại sau khi đã khấu trừ chiết khấu và giá vốn:
  $$\text{Gross Profit} = \text{Net Revenue} - \text{Estimated Cost}$$
  ```dax
  Gross Profit = [Net Revenue] - [Estimated Cost]
  ```

* **Giá trị Đơn hàng Trung bình (Average Order Value - AOV):**  
  Đo lường mức chi tiêu thực tế bình quân trên mỗi đơn hàng:
  $$\text{AOV} = \frac{\text{Net Revenue}}{\text{Total Orders}}$$
  ```dax
  Average Order Value = DIVIDE([Net Revenue], [Total Orders], 0)
  ```

---

### 3.3. Key Performance Indicators - KPIs (Chỉ số hiệu suất then chốt)
Các chỉ số đo lường hiệu quả được so sánh trên tỷ lệ phần trăm (%) để đánh giá mục tiêu và ngưỡng an toàn tài chính:

* **Tỷ suất Lợi nhuận Gộp (%) - Profit Margin %:**  
  *Ngưỡng đánh giá:* Đánh giá khả năng sinh lời trên mỗi đồng doanh thu thuần thu về. Nếu tỷ suất giảm sút trong khi doanh thu tăng thì doanh nghiệp đang chịu rủi ro chi phí/chiết khấu cao.
  $$\text{Profit Margin \%} = \frac{\text{Gross Profit}}{\text{Net Revenue}} \times 100\%$$
  ```dax
  Profit Margin % = DIVIDE([Gross Profit], [Net Revenue], 0)
  ```

* **Tỷ lệ Chiết khấu trên Doanh thu (%) - Discount Rate %:**  
  *Ngưỡng đánh giá:* Kiểm soát mức độ phụ thuộc vào khuyến mãi. Ngưỡng cảnh báo rủi ro khi tỷ lệ chiết khấu vượt quá $25\% - 30\%$ tổng doanh thu gộp.
  $$\text{Discount Rate \%} = \frac{\text{Total Discount}}{\text{Gross Revenue}} \times 100\%$$
  ```dax
  Discount Rate % = DIVIDE([Total Discount], [Gross Revenue], 0)
  ```
