IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'EcommerceDW')
BEGIN
    CREATE DATABASE EcommerceDW;
END
GO

USE EcommerceDW;
GO

-- ========================================================
-- 1. DIMENSION TABLES
-- ========================================================

-- DIM_DATE
IF OBJECT_ID('dbo.DIM_DATE', 'U') IS NOT NULL DROP TABLE dbo.DIM_DATE;
CREATE TABLE dbo.DIM_DATE (
    date_key    INT           NOT NULL PRIMARY KEY,
    full_date   DATE          NOT NULL UNIQUE,
    day         TINYINT       NOT NULL,
    month       TINYINT       NOT NULL,
    month_name  NVARCHAR(20)  NOT NULL,
    quarter     TINYINT       NOT NULL,
    year        SMALLINT      NOT NULL,
    weekday     NVARCHAR(20)  NOT NULL
);

-- DIM_CUSTOMER
IF OBJECT_ID('dbo.DIM_CUSTOMER', 'U') IS NOT NULL DROP TABLE dbo.DIM_CUSTOMER;
CREATE TABLE dbo.DIM_CUSTOMER (
    customer_key        INT            NOT NULL PRIMARY KEY,
    customer_id         VARCHAR(50)    NOT NULL,
    gender              NVARCHAR(30)   NULL,
    age_group           NVARCHAR(30)   NULL,
    acquisition_channel NVARCHAR(100)  NULL,
    signup_date         DATE           NULL,
    zip                 VARCHAR(20)    NULL,
    city                NVARCHAR(100)  NULL
);

-- DIM_PRODUCT
IF OBJECT_ID('dbo.DIM_PRODUCT', 'U') IS NOT NULL DROP TABLE dbo.DIM_PRODUCT;
CREATE TABLE dbo.DIM_PRODUCT (
    product_key  INT             NOT NULL PRIMARY KEY,
    product_id   VARCHAR(50)     NOT NULL,
    product_name NVARCHAR(255)   NULL,
    category     NVARCHAR(100)   NULL,
    segment      NVARCHAR(100)   NULL,
    size         NVARCHAR(30)    NULL,
    color        NVARCHAR(50)    NULL,
    price        DECIMAL(19,4)   NULL,
    cogs         DECIMAL(19,4)   NULL
);

-- DIM_EMPLOYEE
IF OBJECT_ID('dbo.DIM_EMPLOYEE', 'U') IS NOT NULL DROP TABLE dbo.DIM_EMPLOYEE;
CREATE TABLE dbo.DIM_EMPLOYEE (
    employee_key        INT            NOT NULL PRIMARY KEY,
    sales_employee_id   VARCHAR(50)    NULL,
    sales_employee_name NVARCHAR(150)  NULL,
    marital_status      NVARCHAR(30)   NULL,
    education_level     NVARCHAR(100)  NULL,
    years_experience    INT            NULL
);

-- DIM_GEOGRAPHY
IF OBJECT_ID('dbo.DIM_GEOGRAPHY', 'U') IS NOT NULL DROP TABLE dbo.DIM_GEOGRAPHY;
CREATE TABLE dbo.DIM_GEOGRAPHY (
    geography_key INT            NOT NULL PRIMARY KEY,
    zip           VARCHAR(20)    NULL,
    city          NVARCHAR(100)  NULL,
    district      NVARCHAR(100)  NULL,
    region        NVARCHAR(100)  NULL
);

-- DIM_PROMOTION
IF OBJECT_ID('dbo.DIM_PROMOTION', 'U') IS NOT NULL DROP TABLE dbo.DIM_PROMOTION;
CREATE TABLE dbo.DIM_PROMOTION (
    promotion_key        INT             NOT NULL PRIMARY KEY,
    promo_id             VARCHAR(50)     NOT NULL,
    promo_name           NVARCHAR(200)   NULL,
    promo_type           NVARCHAR(100)   NULL,
    discount_value       DECIMAL(19,4)   NULL,
    start_date           DATE            NULL,
    end_date             DATE            NULL,
    applicable_category  NVARCHAR(100)   NULL,
    promo_channel        NVARCHAR(100)   NULL,
    stackable_flag       BIT             NULL,
    min_order_value      DECIMAL(19,4)   NULL
);

-- DIM_SHIPPER
IF OBJECT_ID('dbo.DIM_SHIPPER', 'U') IS NOT NULL DROP TABLE dbo.DIM_SHIPPER;
CREATE TABLE dbo.DIM_SHIPPER (
    shipper_key              INT             NOT NULL PRIMARY KEY,
    shipper_id               VARCHAR(50)     NOT NULL,
    shipper_company          NVARCHAR(200)   NULL,
    shipper_vehicle          NVARCHAR(100)   NULL,
    shipper_rating           DECIMAL(5,2)    NULL,
    delivery_success_rate    DECIMAL(7,4)    NULL,
    shipper_experience_years INT             NULL
);
GO

-- ========================================================
-- 2. FACT TABLES
-- ========================================================

-- FACT_SALES_RETURN
IF OBJECT_ID('dbo.FACT_SALES_RETURN', 'U') IS NOT NULL DROP TABLE dbo.FACT_SALES_RETURN;
CREATE TABLE dbo.FACT_SALES_RETURN (
    order_date_key    INT             NOT NULL,
    customer_key      INT             NOT NULL,
    product_key       INT             NOT NULL,
    employee_key      INT             NULL,
    geography_key     INT             NULL,

    order_id          VARCHAR(50)     NOT NULL,
    order_item_id     VARCHAR(50)     NOT NULL PRIMARY KEY,
    order_status      NVARCHAR(50)    NULL,
    device_type       NVARCHAR(50)    NULL,
    order_source      NVARCHAR(100)   NULL,

    quantity          INT             NOT NULL,
    unit_price        DECIMAL(19,4)   NOT NULL,
    gross_amount      DECIMAL(19,4)   NOT NULL,
    discount_amount   DECIMAL(19,4)   NOT NULL,
    net_amount        DECIMAL(19,4)   NOT NULL,
    estimated_cost    DECIMAL(19,4)   NULL,
    estimated_profit  DECIMAL(19,4)   NULL,
    returned_quantity INT             NOT NULL DEFAULT 0,
    refund_amount     DECIMAL(19,4)   NOT NULL DEFAULT 0,
    return_count      INT             NOT NULL DEFAULT 0,

    CONSTRAINT FK_SALES_DATE
        FOREIGN KEY (order_date_key)
        REFERENCES dbo.DIM_DATE(date_key),

    CONSTRAINT FK_SALES_CUSTOMER
        FOREIGN KEY (customer_key)
        REFERENCES dbo.DIM_CUSTOMER(customer_key),

    CONSTRAINT FK_SALES_PRODUCT
        FOREIGN KEY (product_key)
        REFERENCES dbo.DIM_PRODUCT(product_key),

    CONSTRAINT FK_SALES_EMPLOYEE
        FOREIGN KEY (employee_key)
        REFERENCES dbo.DIM_EMPLOYEE(employee_key),

    CONSTRAINT FK_SALES_GEOGRAPHY
        FOREIGN KEY (geography_key)
        REFERENCES dbo.DIM_GEOGRAPHY(geography_key)
);

-- FACT_INVENTORY
IF OBJECT_ID('dbo.FACT_INVENTORY', 'U') IS NOT NULL DROP TABLE dbo.FACT_INVENTORY;
CREATE TABLE dbo.FACT_INVENTORY (
    snapshot_date_key INT             NOT NULL,
    product_key       INT             NOT NULL,
    stock_on_hand     INT             NULL,
    units_received    INT             NULL,
    units_sold        INT             NULL,
    stockout_days     INT             NULL,
    days_of_supply    DECIMAL(19,4)   NULL,
    fill_rate         DECIMAL(9,6)    NULL,
    stockout_flag     BIT             NULL,
    overstock_flag    BIT             NULL,
    reorder_flag      BIT             NULL,
    sell_through_rate DECIMAL(9,6)    NULL,

    CONSTRAINT PK_FACT_INVENTORY
        PRIMARY KEY (snapshot_date_key, product_key),

    CONSTRAINT FK_INVENTORY_DATE
        FOREIGN KEY (snapshot_date_key)
        REFERENCES dbo.DIM_DATE(date_key),

    CONSTRAINT FK_INVENTORY_PRODUCT
        FOREIGN KEY (product_key)
        REFERENCES dbo.DIM_PRODUCT(product_key)
);

-- FACT_PAYMENT
IF OBJECT_ID('dbo.FACT_PAYMENT', 'U') IS NOT NULL DROP TABLE dbo.FACT_PAYMENT;
CREATE TABLE dbo.FACT_PAYMENT (
    payment_date_key INT             NOT NULL,
    customer_key     INT             NOT NULL,
    order_id         VARCHAR(50)     NOT NULL PRIMARY KEY,
    payment_method   NVARCHAR(100)   NULL,
    payment_value    DECIMAL(19,4)   NOT NULL,
    installments     INT             NULL,

    CONSTRAINT FK_PAYMENT_DATE
        FOREIGN KEY (payment_date_key)
        REFERENCES dbo.DIM_DATE(date_key),

    CONSTRAINT FK_PAYMENT_CUSTOMER
        FOREIGN KEY (customer_key)
        REFERENCES dbo.DIM_CUSTOMER(customer_key)
);

-- FACT_SHIPMENT
IF OBJECT_ID('dbo.FACT_SHIPMENT', 'U') IS NOT NULL DROP TABLE dbo.FACT_SHIPMENT;
CREATE TABLE dbo.FACT_SHIPMENT (
    ship_date_key     INT            NULL,
    delivery_date_key INT            NULL,
    customer_key      INT            NOT NULL,
    geography_key     INT            NULL,
    shipper_key       INT            NOT NULL,
    shipment_id       VARCHAR(100)   NOT NULL PRIMARY KEY,
    order_id          VARCHAR(50)    NOT NULL,
    shipping_fee      DECIMAL(19,4)  NULL,
    delivery_days     INT            NULL,

    CONSTRAINT FK_SHIPMENT_SHIP_DATE
        FOREIGN KEY (ship_date_key)
        REFERENCES dbo.DIM_DATE(date_key),

    CONSTRAINT FK_SHIPMENT_DELIVERY_DATE
        FOREIGN KEY (delivery_date_key)
        REFERENCES dbo.DIM_DATE(date_key),

    CONSTRAINT FK_SHIPMENT_CUSTOMER
        FOREIGN KEY (customer_key)
        REFERENCES dbo.DIM_CUSTOMER(customer_key),

    CONSTRAINT FK_SHIPMENT_GEOGRAPHY
        FOREIGN KEY (geography_key)
        REFERENCES dbo.DIM_GEOGRAPHY(geography_key),

    CONSTRAINT FK_SHIPMENT_SHIPPER
        FOREIGN KEY (shipper_key)
        REFERENCES dbo.DIM_SHIPPER(shipper_key)
);
GO

-- ========================================================
-- 3. BRIDGE TABLE
-- ========================================================

-- BRIDGE_ORDER_ITEM_PROMOTION
IF OBJECT_ID('dbo.BRIDGE_ORDER_ITEM_PROMOTION', 'U') IS NOT NULL DROP TABLE dbo.BRIDGE_ORDER_ITEM_PROMOTION;
CREATE TABLE dbo.BRIDGE_ORDER_ITEM_PROMOTION (
    order_item_id VARCHAR(50) NOT NULL,
    promotion_key INT         NOT NULL,
    promo_id      VARCHAR(50) NULL,

    CONSTRAINT PK_BRIDGE_ORDER_ITEM_PROMOTION
        PRIMARY KEY (order_item_id, promotion_key),

    CONSTRAINT FK_BRIDGE_ORDER_ITEM
        FOREIGN KEY (order_item_id)
        REFERENCES dbo.FACT_SALES_RETURN(order_item_id),

    CONSTRAINT FK_BRIDGE_PROMOTION
        FOREIGN KEY (promotion_key)
        REFERENCES dbo.DIM_PROMOTION(promotion_key)
);
GO

USE EcommerceDW;
GO

-- 1. Thống kê số lượng dòng của từng bảng
SELECT t.name AS TableName, p.rows AS TotalRows
FROM sys.tables t
JOIN sys.partitions p ON t.object_id = p.object_id
WHERE p.index_id IN (0, 1)
ORDER BY p.rows DESC;

-- 2. Truy vấn mẫu phân tích doanh thu theo ngày và danh mục sản phẩm
SELECT TOP 10 
    d.full_date,
    p.category,
    p.product_name,
    SUM(f.quantity) AS total_quantity,
    SUM(f.net_amount) AS total_revenue,
    SUM(f.estimated_profit) AS total_profit
FROM dbo.FACT_SALES_RETURN f
JOIN dbo.DIM_DATE d ON f.order_date_key = d.date_key
JOIN dbo.DIM_PRODUCT p ON f.product_key = p.product_key
GROUP BY d.full_date, p.category, p.product_name
ORDER BY total_revenue DESC;

SELECT
    COUNT(*) AS total_rows,
    SUM(quantity) AS total_quantity,
    SUM(gross_amount) AS total_gross_amount,
    SUM(discount_amount) AS total_discount,
    SUM(net_amount) AS total_net_amount,
    SUM(estimated_cost) AS total_estimated_cost,
    SUM(estimated_profit) AS total_estimated_profit
FROM dbo.FACT_SALES_RETURN;

SELECT
    COUNT(*) AS inconsistent_rows
FROM dbo.FACT_SALES_RETURN
WHERE
    ABS(
        ISNULL(gross_amount, 0)
        - ISNULL(quantity, 0) * ISNULL(unit_price, 0)
    ) > 0.01
    OR ABS(
        ISNULL(net_amount, 0)
        - (ISNULL(gross_amount, 0) - ISNULL(discount_amount, 0))
    ) > 0.01;

USE EcommerceDW;
GO
SELECT
    d.[year] AS RevenueYear,
    d.[month] AS RevenueMonth,
    SUM(f.net_amount) AS NetAmount
FROM dbo.FACT_SALES_RETURN AS f
INNER JOIN dbo.DIM_DATE AS d
    ON f.order_date_key = d.date_key
GROUP BY
    d.[year],
    d.[month]
ORDER BY
    d.[year],
    d.[month];

USE EcommerceDW;
GO
WITH MonthlyRevenue AS (
    SELECT
        d.[year] AS RevenueYear,
        d.[month] AS RevenueMonth,
        SUM(f.net_amount) AS NetAmount
    FROM dbo.FACT_SALES_RETURN AS f
    INNER JOIN dbo.DIM_DATE AS d
        ON f.order_date_key = d.date_key
    GROUP BY
        d.[year],
        d.[month]
)
SELECT
    RevenueYear,
    RevenueMonth,
    NetAmount,
    COUNT(*) OVER () AS TotalMonths
FROM MonthlyRevenue
ORDER BY RevenueYear, RevenueMonth;


SELECT
    COLUMN_NAME,
    DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'DIM_DATE';

SELECT
    COLUMN_NAME,
    DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'ForecastRevenue';

-- Bước 1: Tạo bảng dự báo cho PS5
IF OBJECT_ID('dbo.ForecastRevenue', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.ForecastRevenue
    (
        ForecastDate DATE NOT NULL PRIMARY KEY,
        ForecastRevenue DECIMAL(19,2) NOT NULL,
        ModelName NVARCHAR(100) NOT NULL
    );
END;
GO

-- Bước 2: Thêm 6 tháng dự báo từ kết quả Colab
IF NOT EXISTS (
    SELECT 1 FROM dbo.ForecastRevenue
)
BEGIN
    INSERT INTO dbo.ForecastRevenue
        (ForecastDate, ForecastRevenue, ModelName)
    VALUES
        ('2023-01-01',  58731346, 'Seasonal Naive'),
        ('2023-02-01',  79103096, 'Seasonal Naive'),
        ('2023-03-01', 129591723, 'Seasonal Naive'),
        ('2023-04-01', 133254495, 'Seasonal Naive'),
        ('2023-05-01', 139027887, 'Seasonal Naive'),
        ('2023-06-01', 130756674, 'Seasonal Naive');
END;
GO

-- Bước 3: Kiểm tra kết quả
SELECT
    ForecastDate,
    ForecastRevenue,
    ModelName
FROM dbo.ForecastRevenue
ORDER BY ForecastDate;
GO
