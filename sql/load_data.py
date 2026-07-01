import pandas as pd
from sqlalchemy import create_engine, text
import psycopg2

# Read master data
df = pd.read_csv('data/cleaned/master_data.csv')
print(f"Loaded master data with shape: {df.shape}")

# Database connection parameters
db_params = {
    'host': 'localhost',
    'port': 5432,
    'database': 'bi_platform',
    'user': 'postgres',
    'password': 'Password'
}

# Create SQLAlchemy engine
engine = create_engine(f"postgresql://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{db_params['database']}")

# Create tables if they don't exist
create_tables_sql = """
-- Create dim_customers table
CREATE TABLE dim_customers (
    customer_id TEXT PRIMARY KEY,
    city TEXT,
    state TEXT
);

-- Create dim_products table
CREATE TABLE dim_products (
    product_id TEXT PRIMARY KEY,
    category TEXT
);

-- Create fact_orders table
CREATE TABLE fact_orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT,
    product_id TEXT,
    revenue FLOAT,
    delivery_days FLOAT,
    is_late INT,
    review_score FLOAT,
    order_date DATE,
    FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id),
    FOREIGN KEY (product_id) REFERENCES dim_products(product_id)
);
"""

# Execute table creation (drops tables in correct order)
with engine.connect() as conn:
    # Drop tables in reverse dependency order
    conn.execute(text("DROP TABLE IF EXISTS fact_orders CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS dim_products CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS dim_customers CASCADE"))
    conn.commit()
    
    # Create tables
    conn.execute(text(create_tables_sql))
    conn.commit()
print("Tables created successfully")

# Prepare data for dim_customers (unique customers)
dim_customers_df = df[['customer_id', 'customer_city', 'customer_state']].drop_duplicates()
dim_customers_df.columns = ['customer_id', 'city', 'state']

# Prepare data for dim_products (unique products - keep first occurrence of each product_id)
dim_products_df = df[['product_id', 'product_category_name']].drop_duplicates(subset=['product_id'], keep='first')
dim_products_df.columns = ['product_id', 'category']

# Prepare data for fact_orders (unique orders - keep first occurrence of each order_id)
fact_orders_df = df[['order_id', 'customer_id', 'product_id', 'revenue', 'delivery_days', 'is_late', 'review_score', 'order_purchase_timestamp']].drop_duplicates(subset=['order_id'], keep='first')
fact_orders_df['order_date'] = pd.to_datetime(fact_orders_df['order_purchase_timestamp']).dt.date
fact_orders_df = fact_orders_df.drop(columns=['order_purchase_timestamp'])

# Load data into tables (using append since tables are already dropped and recreated)
dim_customers_df.to_sql('dim_customers', engine, if_exists='append', index=False)
print(f"Loaded {len(dim_customers_df)} customers into dim_customers")

dim_products_df.to_sql('dim_products', engine, if_exists='append', index=False)
print(f"Loaded {len(dim_products_df)} products into dim_products")

fact_orders_df.to_sql('fact_orders', engine, if_exists='append', index=False)
print(f"Loaded {len(fact_orders_df)} orders into fact_orders")

# Run analysis queries
print("\n" + "="*50)
print("DATABASE ANALYSIS")
print("="*50)

with engine.connect() as conn:
    # Total number of orders
    query1 = "SELECT COUNT(*) as total_orders FROM fact_orders"
    result1 = pd.read_sql(query1, conn)
    print(f"\nTotal number of orders: {result1['total_orders'].iloc[0]}")
    
    # Average review score
    query2 = "SELECT AVG(review_score) as avg_review_score FROM fact_orders"
    result2 = pd.read_sql(query2, conn)
    print(f"Average review score: {result2['avg_review_score'].iloc[0]:.2f}")
    
    # Top 5 product categories by revenue
    query3 = """
    SELECT p.category, SUM(f.revenue) as total_revenue
    FROM fact_orders f
    JOIN dim_products p ON f.product_id = p.product_id
    GROUP BY p.category
    ORDER BY total_revenue DESC
    LIMIT 5
    """
    result3 = pd.read_sql(query3, conn)
    print("\nTop 5 product categories by revenue:")
    print(result3.to_string(index=False))
    
    # Which state has most customers
    query4 = """
    SELECT state, COUNT(*) as customer_count
    FROM dim_customers
    GROUP BY state
    ORDER BY customer_count DESC
    LIMIT 1
    """
    result4 = pd.read_sql(query4, conn)
    print(f"\nState with most customers: {result4['state'].iloc[0]} ({result4['customer_count'].iloc[0]} customers)")

print("\n" + "="*50)
print("Database loaded successfully")
print("="*50)
