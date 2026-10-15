# PROBLEM STATEMENT 3: XÁC ĐỊNH GIAI ĐOẠN TĂNG TRƯỞNG VÀ SUY GIẢM DOANH THU

## 1. Ý NGHĨA & MỤC TIÊU KINH DOANH (BUSINESS OBJECTIVE)

* **Bối cảnh & Vấn đề thực tế:**  
  Doanh thu thương mại điện tử thường biến thiên mạnh theo chu kỳ mùa vụ, các chiến dịch khuyến mãi hoặc thay đổi trong hành vi tiêu dùng. Nếu nhà quản trị chỉ nhìn vào doanh số tuyệt đối của từng tháng độc lập mà không đối chiếu với chuỗi thời gian, họ sẽ không thể nhận biết được doanh nghiệp đang thực sự tăng tốc hay đang bước vào chu kỳ thoái trào để kịp thời can thiệp.
* **Mục tiêu phân tích:**  
  1. Tính toán chính xác **Tốc độ tăng trưởng doanh thu theo tháng (Month-over-Month Growth - MoM)** để nhận diện động lực phát triển ngắn hạn.
  2. Đo lường **Tốc độ tăng trưởng cùng kỳ năm trước (Year-over-Year Growth - YoY)** nhằm triệt tiêu yếu tố biến động mùa vụ (Seasonality) và xác định quỹ đạo phát triển dài hạn.
  3. Định vị các **tháng có mức tăng trưởng đột biến (Peaks)** và **tháng sụt giảm sâu (Troughs)** trong toàn bộ chu kỳ 2012–2022.
  4. Phân tích nguyên nhân tăng/giảm dựa trên 2 động lực cốt lõi: biến động về **Số lượng đơn hàng (Volume/Order Count)** hay biến động về **Giá trị trung bình đơn (Price/AOV)**, có gắn liền với chiến dịch khuyến mãi hay không.
  5. Thiết lập cơ chế **Cảnh báo rủi ro sớm (Risk Warning Indicator)** khi doanh thu sụt giảm liên tiếp từ 2 tháng trở lên.
* **Phạm vi triển khai (MOLAP Scope):**  
  Tận dụng tối đa các hàm xử lý chuỗi thời gian (Time-Intelligence) trên trục `DIM_DATE`, kết hợp bóc tách theo chiều Ngành hàng (`DIM_PRODUCT`) và Chiến dịch khuyến mãi (`DIM_PROMOTION` thông qua `BRIDGE_ORDER_ITEM_PROMOTION`).

---

## 2. CÁC BẢNG & CỘT DỮ LIỆU THAM GIA XÂY DỰNG ĐỘ ĐO (DATA INPUTS)

### 2.1. Bảng Fact chính: `FACT_SALES_RETURN`
Bảng ghi nhận toàn bộ các dòng giao dịch bán hàng phục vụ tính toán các biến số thời gian (Grain: 1 dòng / 1 `order_item_id`).

| Cột Dữ Liệu | Kiểu Dữ Liệu | Vai Trò Trong Xây Dựng Measure / Metric |
| :--- | :--- | :--- |
| `order_date_key` | `INT` | Khóa ngoại tham chiếu đến `DIM_DATE[date_key]` dạng số nguyên `YYYYMMDD`; làm điểm tựa cho toàn bộ các phép tính Time-Intelligence. |
| `net_amount` | `DECIMAL(19,4)` | Doanh thu thuần thực tế sau chiết khấu; biến số mục tiêu chính để đo lường mức độ tăng trưởng hoặc suy giảm. |
| `order_id` | `VARCHAR(50)` | Mã định danh đơn hàng; dùng để tính tổng số đơn phát sinh trong kỳ nhằm phân rã nguyên nhân tăng trưởng (do tăng đơn hay tăng giá). |
| `quantity` | `INT` | Số lượng sản phẩm bán ra; đánh giá biến động về mặt sản lượng tiêu thụ giữa các tháng. |
| `order_item_id` | `VARCHAR(50)` | Khóa chính của dòng bán hàng; dùng để liên kết sang bảng cầu nối khuyến mãi (`BRIDGE_ORDER_ITEM_PROMOTION`). |

### 2.2. Các Bảng Dimension tham gia tính toán chuỗi thời gian & cắt lát

| Tên Bảng Dimension | Cột Dữ Liệu Tham Gia | Ý Nghĩa Trong Chiều Phân Tích (Dimensions) |
| :--- | :--- | :--- |
| **`DIM_DATE`** | `date_key`, `full_date`, `year`, `quarter`, `month`, `month_name` | **Trục cốt lõi:** Cung cấp chuỗi ngày liên tục (`full_date` từ 2012 đến 2022) bắt buộc phải có để các hàm DAX như `DATEADD`, `SAMEPERIODLASTYEAR` hoạt động chính xác. |
| **`DIM_PRODUCT`** | `product_key`, `category` | Cắt lát bóc tách cơ cấu ngành hàng nào đóng góp vào đà tăng trưởng hoặc là nguyên nhân kéo tụt doanh thu. |
| **`BRIDGE_ORDER_ITEM_PROMOTION`** | `order_item_id`, `promotion_key` | Bảng cầu nối liên kết mặt hàng bán ra với chương trình khuyến mãi tương ứng. |
| **`DIM_PROMOTION`** | `promotion_key`, `promo_name`, `promo_type` | Kiểm tra các giai đoạn doanh thu tăng đột biến có tương quan trực tiếp với thời điểm chạy chiến dịch khuyến mãi hay không. |

---

## 3. DANH MỤC MEASURES, METRICS & KPIS (CÔNG THỨC TOÁN HỌC & DAX)

### 3.1. Base Measures (Độ đo cơ sở)
Các giá trị nền tảng được dùng làm đầu vào cho các phép so sánh chuỗi thời gian:

* **Doanh thu Thuần Kỳ Hiện tại (Current Period Revenue):**
  $$\text{Net Revenue} = \sum (\text{net\_amount})$$
  ```dax
  Net Revenue = SUM(FACT_SALES_RETURN[net_amount])
  ```

* **Tổng Số Đơn hàng trong Kỳ (Total Orders):**
  ```dax
  Total Orders = DISTINCTCOUNT(FACT_SALES_RETURN[order_id])
  ```

* **Tổng Sản lượng Tiêu thụ trong Kỳ (Total Units Sold):**
  ```dax
  Total Units Sold = SUM(FACT_SALES_RETURN[quantity])
  ```

---

### 3.2. Time-Intelligence Derived Metrics (Chỉ số đo lường chuỗi thời gian)
Các chỉ số so sánh tương quan giữa các mốc thời gian để định vị giai đoạn phát triển:

* **Doanh thu Tháng Liền trước (Prior Month Revenue - $Rev_{M-1}$):**  
  Dịch chuyển ngữ cảnh lọc về đúng 1 tháng trước đó trong lịch dương:
  $$Rev_{M-1} = \text{Calculate}(Net\ Revenue, \text{Month} - 1)$$
  ```dax
  Prior Month Revenue = 
  CALCULATE(
      [Net Revenue],
      DATEADD(DIM_DATE[full_date], -1, MONTH)
  )
  ```

* **Giá trị Chênh lệch Tăng / Giảm Doanh thu Tháng (MoM Growth Value - $\Delta Rev_{MoM}$):**  
  Số tiền tăng thêm hoặc sụt giảm tuyệt đối so với tháng trước:
  $$\Delta Rev_{MoM} = Net\ Revenue_M - Net\ Revenue_{M-1}$$
  ```dax
  MoM Growth Value = 
  IF(
      ISBLANK([Prior Month Revenue]),
      BLANK(),
      [Net Revenue] - [Prior Month Revenue]
  )
  ```

* **Doanh thu Cùng kỳ Năm trước (Same Period Last Year - $Rev_{YoY}$):**  
  Dịch chuyển ngữ cảnh lọc về đúng khoảng thời gian tương ứng của năm trước:
  $$Rev_{YoY} = \text{Calculate}(Net\ Revenue, \text{Year} - 1)$$
  ```dax
  Same Period Last Year Revenue = 
  CALCULATE(
      [Net Revenue],
      SAMEPERIODLASTYEAR(DIM_DATE[full_date])
  )
  ```

* **Giá trị Chênh lệch Tăng / Giảm Cùng kỳ (YoY Growth Value - $\Delta Rev_{YoY}$):**  
  $$\Delta Rev_{YoY} = Net\ Revenue_{Year} - Net\ Revenue_{Year-1}$$
  ```dax
  YoY Growth Value = 
  IF(
      ISBLANK([Same Period Last Year Revenue]),
      BLANK(),
      [Net Revenue] - [Same Period Last Year Revenue]
  )
  ```

---

### 3.3. Key Performance Indicators & Risk Alerts (KPIs & Cảnh báo rủi ro)
Các chỉ số đo lường tốc độ phát triển và nhận diện các mốc cảnh báo nghiêm trọng:

* **Tốc độ Tăng trưởng Doanh thu theo Tháng (%) - MoM Growth %:**  
  *Ý nghĩa:* Tỷ lệ phần trăm biến động ngắn hạn giữa 2 tháng liền kề.  
  $$\text{MoM Growth \%} = \frac{Net\ Revenue_M - Net\ Revenue_{M-1}}{Net\ Revenue_{M-1}} \times 100\%$$
  ```dax
  MoM Growth % = 
  DIVIDE([MoM Growth Value], [Prior Month Revenue], 0)
  ```

* **Tốc độ Tăng trưởng Cùng kỳ Năm trước (%) - YoY Growth %:**  
  *Ý nghĩa:* Tỷ lệ phần trăm tăng trưởng dài hạn đã triệt tiêu yếu tố thời vụ.  
  $$\text{YoY Growth \%} = \frac{Net\ Revenue_{Year} - Net\ Revenue_{Year-1}}{Net\ Revenue_{Year-1}} \times 100\%$$
  ```dax
  YoY Growth % = 
  DIVIDE([YoY Growth Value], [Same Period Last Year Revenue], 0)
  ```

* **Chỉ số Cảnh báo Suy giảm Liên tiếp (Consecutive Decline Alert):**  
  *Ý nghĩa & Quy tắc ngưỡng (Threshold Rule):* Nếu tốc độ tăng trưởng tháng này âm ($\text{MoM} < 0$) và tháng trước đó cũng âm ($\text{MoM}_{M-1} < 0$), hệ thống kích hoạt trạng thái cảnh báo nguy cơ suy thoái liên tiếp.
  ```dax
  Decline Warning Flag = 
  VAR CurrentMoM = [MoM Growth %]
  VAR PrevMoM = 
      CALCULATE(
          [MoM Growth %],
          DATEADD(DIM_DATE[full_date], -1, MONTH)
      )
  RETURN
      IF(
          ISBLANK(CurrentMoM) || ISBLANK(PrevMoM),
          "CHƯA ĐỦ DỮ LIỆU",
          IF(
              CurrentMoM < 0 && PrevMoM < 0,
              "CẢNH BÁO: SUY GIẢM 2 THÁNG LIÊN TIẾP",
              "BÌNH THƯỜNG"
          )
      )
  ```
