-- Customer Dimension Table
CREATE TABLE dim_customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    city VARCHAR(100),
    state VARCHAR(50)
);

-- Product Dimension Table
CREATE TABLE dim_products (
    product_id VARCHAR(50) PRIMARY KEY,
    category VARCHAR(100)
);

-- Orders Fact Table
CREATE TABLE fact_orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50),
    product_id VARCHAR(50),
    revenue DECIMAL(10, 2),
    delivery_days INTEGER,
    is_late INTEGER,
    review_score INTEGER,
    order_date DATE,
    FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id),
    FOREIGN KEY (product_id) REFERENCES dim_products(product_id)
);
