from sqlalchemy import create_engine, text
import pandas as pd

DB_HOST = "ep-green-breeze-at9hxpbl-pooler.c-9.us-east-1.aws.neon.tech"
DB_PORT = 5432
DB_NAME = "neondb"
DB_USER = "neondb_owner"
DB_PASSWORD = "npg_TvdFLCn29DoZ"

CONNECTION_STRING = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"

engine = create_engine(CONNECTION_STRING)

# Read master data
df = pd.read_csv('data/cleaned/master_data.csv')
print(f"Loaded master data with shape: {df.shape}")

# Drop tables if exist then create fresh
with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS fact_orders"))
    conn.execute(text("DROP TABLE IF EXISTS dim_customers"))
    conn.execute(text("DROP TABLE IF EXISTS dim_products"))
    conn.commit()
    print("Tables dropped successfully")

# Create all 3 tables in public schema
create_tables_sql = """
CREATE TABLE dim_customers (
    customer_id TEXT PRIMARY KEY,
    city TEXT,
    state TEXT
);

CREATE TABLE dim_products (
    product_id TEXT PRIMARY KEY,
    category TEXT
);

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

with engine.connect() as conn:
    conn.execute(text(create_tables_sql))
    conn.commit()
    print("Tables created successfully")

# Prepare data for dim_customers (unique customers)
dim_customers_df = df[['customer_id', 'customer_city', 'customer_state']].drop_duplicates()
dim_customers_df.columns = ['customer_id', 'city', 'state']

# Prepare data for dim_products (unique products)
dim_products_df = df[['product_id', 'product_category_name']].drop_duplicates(subset=['product_id'], keep='first')
dim_products_df.columns = ['product_id', 'category']

# Prepare data for fact_orders (unique orders)
fact_orders_df = df[['order_id', 'customer_id', 'product_id', 'revenue', 'delivery_days', 'is_late', 'review_score', 'order_purchase_timestamp']].drop_duplicates(subset=['order_id'], keep='first')
fact_orders_df['order_date'] = pd.to_datetime(fact_orders_df['order_purchase_timestamp']).dt.date
fact_orders_df = fact_orders_df.drop(columns=['order_purchase_timestamp'])

# Load data into tables (load dimension tables first, then fact table with proper transaction handling)
with engine.begin() as conn:
    dim_customers_df.to_sql('dim_customers', conn, if_exists='append', index=False)
    print(f"Loaded {len(dim_customers_df)} customers into dim_customers")

    dim_products_df.to_sql('dim_products', conn, if_exists='append', index=False)
    print(f"Loaded {len(dim_products_df)} products into dim_products")

    fact_orders_df.to_sql('fact_orders', conn, if_exists='append', index=False)
    print(f"Loaded {len(fact_orders_df)} orders into fact_orders")

print("Database loaded successfully")
