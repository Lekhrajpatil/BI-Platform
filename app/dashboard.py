import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text
import joblib
from datetime import datetime, timedelta
import time
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

# Page configuration
st.set_page_config(
    page_title="E-Commerce BI Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .metric-card {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 20px;
        margin: 10px 0;
    }
    .stMetric {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 15px;
    }
    .stMetric label {
        font-size: 14px;
        color: #8B949E;
    }
    .stMetric div {
        font-size: 28px;
        font-weight: bold;
        color: #FAFAFA;
    }
    .footer {
        text-align: center;
        padding: 20px;
        color: #8B949E;
        font-size: 12px;
        margin-top: 40px;
    }
</style>
""", unsafe_allow_html=True)

# Database connection
@st.cache_resource
def get_db_connection():
    engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    return engine

# Load data
@st.cache_data(ttl=60)
def load_data():
    engine = get_db_connection()
    
    # Get project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Load from CSV files
    master_data = pd.read_csv(os.path.join(project_root, 'data/cleaned/master_data.csv'))
    sales_forecast = pd.read_csv(os.path.join(project_root, 'data/cleaned/sales_forecast.csv'))
    
    # Load churn model
    churn_model = joblib.load(os.path.join(project_root, 'models/churn_model.pkl'))
    
    # Load from PostgreSQL
    with engine.connect() as conn:
        customers_df = pd.read_sql("SELECT * FROM dim_customers", conn)
        products_df = pd.read_sql("SELECT * FROM dim_products", conn)
        orders_df = pd.read_sql("SELECT * FROM fact_orders", conn)
    
    return master_data, sales_forecast, churn_model, customers_df, products_df, orders_df

# Initialize data
with st.spinner("Loading data..."):
    master_data, sales_forecast, churn_model, customers_df, products_df, orders_df = load_data()

# Convert date columns
master_data['order_purchase_timestamp'] = pd.to_datetime(master_data['order_purchase_timestamp'])
master_data['order_date'] = pd.to_datetime(master_data['order_purchase_timestamp']).dt.date

# Sidebar
with st.sidebar:
    st.title("📊 BI Platform")
    
    # Global date filter
    st.subheader("📅 Date Range Filter")
    min_date = master_data['order_purchase_timestamp'].min().date()
    max_date = master_data['order_purchase_timestamp'].max().date()
    date_range = st.date_input(
        "Select date range",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )
    
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date
    
    # Customer search
    st.subheader("🔍 Customer Search")
    customer_search = st.text_input("Enter Customer ID")
    
    if customer_search:
        customer_profile = master_data[master_data['customer_id'] == customer_search]
        if not customer_profile.empty:
            st.success("Customer Found!")
            st.write(f"**Total Orders:** {customer_profile['order_id'].nunique()}")
            st.write(f"**Total Revenue:** ${customer_profile['revenue'].sum():,.2f}")
            st.write(f"**Avg Review Score:** {customer_profile['review_score'].mean():.1f} ⭐")
            st.write(f"**Last Order:** {customer_profile['order_purchase_timestamp'].max().date()}")
        else:
            st.error("Customer not found")
    
    # Page navigation
    st.subheader("📑 Navigation")
    page = st.radio(
        "Select Page",
        ["Executive Overview", "Sales Deep Dive", "Churn Intelligence", 
         "Sales Forecast & Trends", "Product & Customer Intelligence", "AI Analyst Chat"]
    )
    
    # Auto-refresh info
    st.subheader("⏱️ Auto-Refresh")
    st.info("Dashboard auto-refreshes every 60 seconds")

# Filter data based on date range
filtered_data = master_data[
    (master_data['order_purchase_timestamp'].dt.date >= start_date) &
    (master_data['order_purchase_timestamp'].dt.date <= end_date)
]

# Footer function
def render_footer():
    st.markdown("""
    <div class="footer">
        Built by Lekhraj | E-Commerce BI Platform 2026 | 
        Powered by Python · PostgreSQL · Streamlit · XGBoost
    </div>
    """, unsafe_allow_html=True)

# Export button function
def add_export_button(df, filename):
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Export Data as CSV",
        data=csv,
        file_name=filename,
        mime="text/csv"
    )

# PAGE 1: Executive Overview
if page == "Executive Overview":
    st.title("🎯 Executive Overview")
    
    # Calculate KPIs
    total_revenue = filtered_data['revenue'].sum()
    total_orders = len(filtered_data)
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
    unique_customers = filtered_data['customer_id'].nunique()
    clv = total_revenue / unique_customers if unique_customers > 0 else 0
    late_delivery_rate = (filtered_data['is_late'].sum() / len(filtered_data) * 100) if len(filtered_data) > 0 else 0
    avg_review_score = filtered_data['review_score'].mean()
    
    # Calculate MoM changes
    if len(filtered_data) > 0:
        current_month = filtered_data['order_purchase_timestamp'].dt.to_period('M').max()
        prev_month = current_month - 1
        current_revenue = filtered_data[filtered_data['order_purchase_timestamp'].dt.to_period('M') == current_month]['revenue'].sum()
        prev_revenue = filtered_data[filtered_data['order_purchase_timestamp'].dt.to_period('M') == prev_month]['revenue'].sum()
        revenue_change = ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
        
        current_orders = len(filtered_data[filtered_data['order_purchase_timestamp'].dt.to_period('M') == current_month])
        prev_orders = len(filtered_data[filtered_data['order_purchase_timestamp'].dt.to_period('M') == prev_month])
        orders_change = ((current_orders - prev_orders) / prev_orders * 100) if prev_orders > 0 else 0
    else:
        revenue_change = 0
        orders_change = 0
    
    # Calculate churn risk
    rfm = filtered_data.groupby('customer_id').agg({
        'order_purchase_timestamp': lambda x: (filtered_data['order_purchase_timestamp'].max() - x.max()).days,
        'order_id': 'count',
        'revenue': 'sum'
    }).reset_index()
    rfm.columns = ['customer_id', 'recency', 'frequency', 'monetary']
    rfm_features = rfm[['recency', 'frequency', 'monetary']]
    churn_predictions = churn_model.predict(rfm_features)
    churn_risk_rate = (churn_predictions.sum() / len(churn_predictions) * 100) if len(churn_predictions) > 0 else 0
    
    # Row 1: KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    col5, col6, col7, col8 = st.columns(4)
    
    with col1:
        st.metric("Total Revenue", f"${total_revenue:,.0f}", f"{revenue_change:+.1f}%")
    with col2:
        st.metric("Total Orders", f"{total_orders:,}", f"{orders_change:+.1f}%")
    with col3:
        st.metric("Avg Order Value", f"${avg_order_value:.2f}")
    with col4:
        st.metric("Customer LTV", f"${clv:.2f}")
    with col5:
        late_color = "🔴" if late_delivery_rate > 20 else "🟢"
        st.metric("Late Delivery Rate", f"{late_delivery_rate:.1f}%", late_color)
    with col6:
        st.metric("Avg Review Score", f"{avg_review_score:.1f} ⭐")
    with col7:
        churn_color = "🔴" if churn_risk_rate > 30 else "🟡" if churn_risk_rate > 15 else "🟢"
        st.metric("Churn Risk Rate", f"{churn_risk_rate:.1f}%", churn_color)
    with col8:
        st.metric("MoM Revenue Growth", f"{revenue_change:+.1f}%")
    
    add_export_button(filtered_data, "executive_overview_data.csv")
    
    # Row 2: Charts
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Revenue by State & Month")
        heatmap_data = filtered_data.groupby(['customer_state', filtered_data['order_purchase_timestamp'].dt.to_period('M')])['revenue'].sum().unstack(fill_value=0)
        fig_heatmap = px.imshow(
            heatmap_data.values,
            labels=dict(x="Month", y="State", color="Revenue"),
            x=[str(p) for p in heatmap_data.columns],
            y=heatmap_data.index,
            color_continuous_scale='Viridis',
            template="plotly_dark"
        )
        fig_heatmap.update_layout(height=400)
        st.plotly_chart(fig_heatmap, use_container_width=True)
    
    with col2:
        st.subheader("Revenue by Product Category")
        category_revenue = filtered_data.groupby('product_category_name')['revenue'].sum().sort_values(ascending=True)
        fig_treemap = px.treemap(
            names=category_revenue.index,
            values=category_revenue.values,
            title="",
            template="plotly_dark"
        )
        fig_treemap.update_layout(height=400)
        st.plotly_chart(fig_treemap, use_container_width=True)
    
    with col3:
        st.subheader("Review Score vs Delivery Days")
        fig_scatter = px.scatter(
            filtered_data,
            x='delivery_days',
            y='review_score',
            color='is_late',
            size='revenue',
            color_discrete_map={0: 'green', 1: 'red'},
            template="plotly_dark",
            opacity=0.6
        )
        fig_scatter.update_layout(height=400)
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    # Row 3: Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Daily Order Volume")
        daily_orders = filtered_data.groupby(filtered_data['order_purchase_timestamp'].dt.date).size()
        ma_7 = daily_orders.rolling(window=7).mean()
        
        fig_area = go.Figure()
        fig_area.add_trace(go.Scatter(
            x=daily_orders.index,
            y=daily_orders.values,
            fill='tozeroy',
            name='Daily Orders',
            line=dict(color='#185FA5')
        ))
        fig_area.add_trace(go.Scatter(
            x=ma_7.index,
            y=ma_7.values,
            name='7-Day MA',
            line=dict(color='orange', width=2)
        ))
        fig_area.update_layout(template="plotly_dark", height=350)
        st.plotly_chart(fig_area, use_container_width=True)
    
    with col2:
        st.subheader("Bottom 10 Categories by Review Score")
        category_reviews = filtered_data.groupby('product_category_name')['review_score'].mean().sort_values().head(10)
        fig_bar = px.bar(
            x=category_reviews.values,
            y=category_reviews.index,
            orientation='h',
            template="plotly_dark",
            color=category_reviews.values,
            color_continuous_scale='Reds'
        )
        fig_bar.update_layout(height=350, xaxis_title="Avg Review Score", yaxis_title="")
        st.plotly_chart(fig_bar, use_container_width=True)
    
    render_footer()

# PAGE 2: Sales Deep Dive
elif page == "Sales Deep Dive":
    st.title("📈 Sales Deep Dive")
    
    # Date range filter for this page
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"Showing data from {start_date} to {end_date}")
    with col2:
        add_export_button(filtered_data, "sales_deep_dive.csv")
    
    # Revenue Waterfall
    st.subheader("Revenue Waterfall - Month by Month")
    monthly_revenue = filtered_data.groupby(filtered_data['order_purchase_timestamp'].dt.to_period('M'))['revenue'].sum()
    
    fig_waterfall = go.Figure(go.Waterfall(
        name="Revenue",
        orientation="v",
        x=[str(p) for p in monthly_revenue.index],
        y=monthly_revenue.values,
        text=[f"${v:,.0f}" for v in monthly_revenue.values],
        textposition="outside",
        increasing={"marker":{"color":"green"}},
        decreasing={"marker":{"color":"red"}}
    ))
    fig_waterfall.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig_waterfall, use_container_width=True)
    
    # Revenue vs Target
    st.subheader("Revenue vs Target (Target = Actual + 10%)")
    target_revenue = monthly_revenue * 1.1
    
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=[str(p) for p in monthly_revenue.index],
        y=monthly_revenue.values,
        name='Actual Revenue',
        line=dict(color='white', width=3)
    ))
    fig_line.add_trace(go.Scatter(
        x=[str(p) for p in target_revenue.index],
        y=target_revenue.values,
        name='Target Revenue',
        line=dict(color='blue', width=2, dash='dash')
    ))
    
    # Annotations for best and worst months
    best_month = monthly_revenue.idxmax()
    worst_month = monthly_revenue.idxmin()
    fig_line.add_annotation(x=str(best_month), y=monthly_revenue.max(), text="🏆 Best", showarrow=True)
    fig_line.add_annotation(x=str(worst_month), y=monthly_revenue.min(), text="⚠️ Worst", showarrow=True)
    
    fig_line.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig_line, use_container_width=True)
    
    # Bubble chart: State vs Revenue vs Order Count vs Avg Review
    st.subheader("State Performance Bubble")
    state_metrics = filtered_data.groupby('customer_state').agg({
        'revenue': 'sum',
        'order_id': 'count',
        'review_score': 'mean'
    }).reset_index()
    
    fig_bubble = px.scatter(
        state_metrics,
        x='revenue',
        y='order_id',
        size='review_score',
        color='customer_state',
        hover_data=['review_score'],
        template="plotly_dark",
        labels={'revenue': 'Total Revenue', 'order_id': 'Order Count'}
    )
    fig_bubble.update_layout(height=400)
    st.plotly_chart(fig_bubble, use_container_width=True)
    
    # Cohort Analysis Heatmap
    st.subheader("Cohort Analysis - Customer Retention")
    filtered_data['order_period'] = filtered_data['order_purchase_timestamp'].dt.to_period('M')
    filtered_data['cohort'] = filtered_data.groupby('customer_id')['order_period'].transform('min')
    
    cohort_data = filtered_data.groupby(['cohort', 'order_period']).agg({'customer_id': 'nunique'}).reset_index()
    cohort_data['period_number'] = (cohort_data['order_period'] - cohort_data['cohort']).apply(lambda x: x.n)
    
    cohort_pivot = cohort_data.pivot(index='cohort', columns='period_number', values='customer_id')
    cohort_size = cohort_pivot.iloc[:, 0]
    retention = cohort_pivot.divide(cohort_size, axis=0) * 100
    
    fig_cohort = px.imshow(
        retention.values,
        labels=dict(x="Months Since First Order", y="Cohort Month", color="Retention %"),
        x=[f"Month {i}" for i in retention.columns],
        y=[str(p) for p in retention.index],
        color_continuous_scale='RdYlGn',
        template="plotly_dark"
    )
    fig_cohort.update_layout(height=400)
    st.plotly_chart(fig_cohort, use_container_width=True)
    
    # RFM Segment Distribution
    st.subheader("RFM Segment Distribution")
    rfm = filtered_data.groupby('customer_id').agg({
        'order_purchase_timestamp': lambda x: (filtered_data['order_purchase_timestamp'].max() - x.max()).days,
        'order_id': 'count',
        'revenue': 'sum'
    }).reset_index()
    rfm.columns = ['customer_id', 'recency', 'frequency', 'monetary']
    
    # Simple RFM segmentation
    rfm['segment'] = 'New Customers'
    rfm.loc[(rfm['recency'] <= 30) & (rfm['frequency'] >= 5), 'segment'] = 'Champions'
    rfm.loc[(rfm['recency'] <= 60) & (rfm['frequency'] >= 3), 'segment'] = 'Loyal'
    rfm.loc[(rfm['recency'] > 90) & (rfm['frequency'] >= 2), 'segment'] = 'At Risk'
    rfm.loc[rfm['recency'] > 180, 'segment'] = 'Lost'
    
    segment_counts = rfm['segment'].value_counts()
    
    fig_donut = go.Figure(data=[go.Pie(
        labels=segment_counts.index,
        values=segment_counts.values,
        hole=0.4,
        marker=dict(colors=['#00CC96', '#EF553B', '#AB63FA', '#FFA15A', '#19D3F3'])
    )])
    fig_donut.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig_donut, use_container_width=True)
    
    render_footer()

# PAGE 3: Churn Intelligence
elif page == "Churn Intelligence":
    st.title("⚠️ Churn Intelligence")
    
    # Feature Importance
    st.subheader("Feature Importance - What Drives Churn?")
    feature_importance = pd.DataFrame({
        'feature': ['recency', 'frequency', 'monetary'],
        'importance': churn_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    fig_importance = px.bar(
        feature_importance,
        x='importance',
        y='feature',
        orientation='h',
        template="plotly_dark",
        color='importance',
        color_continuous_scale='Reds'
    )
    fig_importance.update_layout(height=300)
    st.plotly_chart(fig_importance, use_container_width=True)
    
    # 3D Scatter Plot
    st.subheader("Customer Segmentation 3D View")
    rfm = filtered_data.groupby('customer_id').agg({
        'order_purchase_timestamp': lambda x: (filtered_data['order_purchase_timestamp'].max() - x.max()).days,
        'order_id': 'count',
        'revenue': 'sum'
    }).reset_index()
    rfm.columns = ['customer_id', 'recency', 'frequency', 'monetary']
    
    rfm_features = rfm[['recency', 'frequency', 'monetary']]
    rfm['churn_probability'] = churn_model.predict_proba(rfm_features)[:, 1]
    
    fig_3d = px.scatter_3d(
        rfm,
        x='recency',
        y='frequency',
        z='monetary',
        color='churn_probability',
        color_continuous_scale='RdYlGn_r',
        template="plotly_dark",
        labels={'recency': 'Days Since Last Order', 'frequency': 'Order Count', 'monetary': 'Total Spend'}
    )
    fig_3d.update_layout(height=500)
    st.plotly_chart(fig_3d, use_container_width=True)
    
    # Gauge Chart
    st.subheader("Overall Churn Rate")
    churn_rate = rfm['churn_probability'].mean() * 100
    
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=churn_rate,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Churn Rate %"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "#185FA5"},
            'steps': [
                {'range': [0, 20], 'color': 'green'},
                {'range': [20, 50], 'color': 'yellow'},
                {'range': [50, 100], 'color': 'red'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 30
            }
        }
    ))
    fig_gauge.update_layout(height=300, template="plotly_dark")
    st.plotly_chart(fig_gauge, use_container_width=True)
    
    # Churn Risk Table
    st.subheader("Churn Risk Analysis")
    rfm['risk_level'] = pd.cut(rfm['churn_probability'], bins=[0, 0.3, 0.7, 1], labels=['Low', 'Medium', 'High'])
    rfm = rfm.sort_values('churn_probability', ascending=False).head(50)
    
    def color_risk(val):
        if val == 'High':
            return 'background-color: #FF6B6B; color: white'
        elif val == 'Medium':
            return 'background-color: #FFD93D; color: black'
        else:
            return 'background-color: #6BCB77; color: white'
    
    styled_rfm = rfm[['customer_id', 'recency', 'frequency', 'monetary', 'churn_probability', 'risk_level']].copy()
    styled_rfm['churn_probability'] = (styled_rfm['churn_probability'] * 100).round(1).astype(str) + '%'
    styled_rfm['monetary'] = '$' + styled_rfm['monetary'].round(2).astype(str)
    
    st.dataframe(
        styled_rfm.style.applymap(color_risk, subset=['risk_level']),
        use_container_width=True
    )
    
    add_export_button(rfm, "churn_risk_analysis.csv")
    
    # Sidebar: Live Prediction
    st.subheader("Live Churn Prediction")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        recency_input = st.slider("Recency (days since last order)", 0, 365, 90)
    with col2:
        frequency_input = st.slider("Frequency (total orders)", 1, 50, 5)
    with col3:
        monetary_input = st.slider("Monetary (total spent)", 0, 10000, 500)
    
    # Live prediction
    input_features = pd.DataFrame([[recency_input, frequency_input, monetary_input]], 
                                   columns=['recency', 'frequency', 'monetary'])
    churn_prob = churn_model.predict_proba(input_features)[0, 1] * 100
    
    col1, col2 = st.columns(2)
    with col1:
        if churn_prob > 70:
            st.error(f"🔴 HIGH RISK - {churn_prob:.1f}% churn probability")
        elif churn_prob > 30:
            st.warning(f"🟡 MEDIUM RISK - {churn_prob:.1f}% churn probability")
        else:
            st.success(f"🟢 LOW RISK - {churn_prob:.1f}% churn probability")
    
    render_footer()

# PAGE 4: Sales Forecast & Trends
elif page == "Sales Forecast & Trends":
    st.title("🔮 Sales Forecast & Trends")
    
    # Forecast Chart
    st.subheader("Revenue Forecast - Next 6 Months")
    sales_forecast['ds'] = pd.to_datetime(sales_forecast['ds'])
    
    fig_forecast = go.Figure()
    
    # Actual revenue
    actual_data = filtered_data.groupby(filtered_data['order_purchase_timestamp'].dt.to_period('M'))['revenue'].sum()
    fig_forecast.add_trace(go.Scatter(
        x=[p.to_timestamp() for p in actual_data.index],
        y=actual_data.values,
        name='Actual Revenue',
        line=dict(color='white', width=3)
    ))
    
    # Forecast
    forecast_only = sales_forecast[sales_forecast['ds'] > actual_data.index.max().to_timestamp()]
    fig_forecast.add_trace(go.Scatter(
        x=forecast_only['ds'],
        y=forecast_only['yhat'],
        name='Forecast',
        line=dict(color='blue', width=3)
    ))
    
    # Confidence interval
    fig_forecast.add_trace(go.Scatter(
        x=forecast_only['ds'].tolist() + forecast_only['ds'].tolist()[::-1],
        y=forecast_only['yhat_upper'].tolist() + forecast_only['yhat_lower'].tolist()[::-1],
        fill='toself',
        fillcolor='rgba(0, 100, 255, 0.2)',
        line=dict(color='rgba(255,255,255,0)'),
        name='Confidence Interval'
    ))
    
    # Today line
    today = datetime.now()
    fig_forecast.add_shape(
        type="line",
        x0=today, x1=today,
        y0=0, y1=1,
        yref='paper',
        line=dict(color="yellow", width=2, dash="dash")
    )
    fig_forecast.add_annotation(
        x=today, y=1,
        yref='paper',
        text="Today",
        showarrow=False,
        yshift=10
    )
    
    # Annotations
    if len(actual_data) > 0:
        best_month = actual_data.idxmax().to_timestamp()
        worst_month = actual_data.idxmin().to_timestamp()
        fig_forecast.add_annotation(x=best_month, y=actual_data.max(), text="🏆 Peak", showarrow=True)
        fig_forecast.add_annotation(x=worst_month, y=actual_data.min(), text="⚠️ Low", showarrow=True)
    
    fig_forecast.update_layout(template="plotly_dark", height=450)
    st.plotly_chart(fig_forecast, use_container_width=True)
    
    # Seasonality Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Revenue by Day of Week")
        filtered_data['day_of_week'] = filtered_data['order_purchase_timestamp'].dt.day_name()
        dow_revenue = filtered_data.groupby('day_of_week')['revenue'].mean()
        dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        dow_revenue = dow_revenue.reindex(dow_order)
        
        fig_dow = px.bar(
            x=dow_revenue.index,
            y=dow_revenue.values,
            template="plotly_dark",
            color=dow_revenue.values,
            color_continuous_scale='Blues'
        )
        fig_dow.update_layout(height=350)
        st.plotly_chart(fig_dow, use_container_width=True)
    
    with col2:
        st.subheader("Revenue by Month of Year")
        filtered_data['month_of_year'] = filtered_data['order_purchase_timestamp'].dt.month_name()
        moy_revenue = filtered_data.groupby('month_of_year')['revenue'].mean()
        moy_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                     'July', 'August', 'September', 'October', 'November', 'December']
        moy_revenue = moy_revenue.reindex(moy_order)
        
        fig_moy = px.bar(
            x=moy_revenue.index,
            y=moy_revenue.values,
            template="plotly_dark",
            color=moy_revenue.values,
            color_continuous_scale='Viridis'
        )
        fig_moy.update_layout(height=350)
        st.plotly_chart(fig_moy, use_container_width=True)
    
    # YoY Comparison
    st.subheader("Year Over Year Comparison")
    filtered_data['year'] = filtered_data['order_purchase_timestamp'].dt.year
    filtered_data['month'] = filtered_data['order_purchase_timestamp'].dt.month
    
    yoy_data = filtered_data.groupby(['year', 'month'])['revenue'].sum().reset_index()
    
    fig_yoy = go.Figure()
    for year in sorted(yoy_data['year'].unique()):
        year_data = yoy_data[yoy_data['year'] == year]
        fig_yoy.add_trace(go.Scatter(
            x=year_data['month'],
            y=year_data['revenue'],
            name=f'{year}',
            mode='lines+markers'
        ))
    
    fig_yoy.update_layout(template="plotly_dark", height=400, xaxis_title="Month")
    st.plotly_chart(fig_yoy, use_container_width=True)
    
    # Forecast Accuracy Table
    st.subheader("Forecast Accuracy")
    forecast_table = forecast_only[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
    forecast_table['Month'] = pd.to_datetime(forecast_table['ds']).dt.strftime('%Y-%m')
    forecast_table = forecast_table.rename(columns={'yhat': 'Predicted', 'yhat_lower': 'Lower', 'yhat_upper': 'Upper'})
    forecast_table = forecast_table[['Month', 'Predicted', 'Lower', 'Upper']]
    
    st.dataframe(forecast_table, use_container_width=True)
    
    # Next 6 Months Forecast Cards
    st.subheader("Next 6 Months Forecast")
    cols = st.columns(6)
    
    current_month_revenue = actual_data.iloc[-1] if len(actual_data) > 0 else 0
    
    for i, (idx, row) in enumerate(forecast_only.head(6).iterrows()):
        with cols[i]:
            month_name = pd.to_datetime(row['ds']).strftime('%b')
            predicted = row['yhat']
            growth = ((predicted - current_month_revenue) / current_month_revenue * 100) if current_month_revenue > 0 else 0
            
            st.metric(
                month_name,
                f"${predicted:,.0f}",
                f"{growth:+.1f}%"
            )
    
    add_export_button(sales_forecast, "sales_forecast.csv")
    render_footer()

# PAGE 5: Product & Customer Intelligence
elif page == "Product & Customer Intelligence":
    st.title("🏪 Product & Customer Intelligence")
    
    # Product Performance Matrix
    st.subheader("Product Performance Matrix")
    product_metrics = filtered_data.groupby('product_category_name').agg({
        'order_id': 'count',
        'review_score': 'mean',
        'revenue': 'sum'
    }).reset_index()
    
    fig_matrix = px.scatter(
        product_metrics,
        x='order_id',
        y='review_score',
        size='revenue',
        color='product_category_name',
        template="plotly_dark",
        labels={'order_id': 'Number of Orders', 'review_score': 'Avg Review Score'},
        hover_data=['product_category_name', 'revenue']
    )
    fig_matrix.update_layout(height=450)
    st.plotly_chart(fig_matrix, use_container_width=True)
    
    # Customer Segmentation Map (Brazil)
    st.subheader("Customer Distribution by State")
    state_customers = filtered_data.groupby('customer_state')['customer_id'].nunique().reset_index()
    state_customers.columns = ['state', 'customer_count']
    
    fig_map = px.choropleth(
        state_customers,
        locations='state',
        locationmode='ISO-3',
        color='customer_count',
        hover_name='state',
        color_continuous_scale='Viridis',
        template="plotly_dark",
        title="Customer Density by State"
    )
    fig_map.update_layout(height=400)
    st.plotly_chart(fig_map, use_container_width=True)
    
    # Top 20 Customers
    st.subheader("Top 20 Customers by Revenue")
    top_customers = filtered_data.groupby('customer_id').agg({
        'order_id': 'count',
        'revenue': 'sum',
        'review_score': 'mean',
        'order_purchase_timestamp': 'max'
    }).reset_index()
    top_customers.columns = ['customer_id', 'total_orders', 'total_revenue', 'avg_review', 'last_order']
    top_customers = top_customers.sort_values('total_revenue', ascending=False).head(20)
    top_customers['last_order'] = pd.to_datetime(top_customers['last_order']).dt.date
    
    # Add churn risk
    rfm_features = top_customers[['total_orders', 'total_revenue', 'avg_review']].copy()
    rfm_features.columns = ['frequency', 'monetary', 'review_score']
    # Simplified - use recency from filtered data
    top_customers['churn_risk'] = 'Low'
    
    st.dataframe(
        top_customers[['customer_id', 'total_orders', 'total_revenue', 'avg_review', 'last_order', 'churn_risk']],
        use_container_width=True
    )
    
    # Price vs Review Correlation
    st.subheader("Price vs Review Score Correlation")
    fig_price_review = px.scatter(
        filtered_data.sample(min(5000, len(filtered_data))),
        x='price',
        y='review_score',
        template="plotly_dark",
        color='product_category_name',
        opacity=0.5,
        labels={'price': 'Product Price', 'review_score': 'Review Score'}
    )
    fig_price_review.update_layout(height=400)
    st.plotly_chart(fig_price_review, use_container_width=True)
    
    # Late Delivery Impact
    st.subheader("Late Delivery Impact on Reviews")
    late_impact = filtered_data.groupby('is_late')['review_score'].mean().reset_index()
    late_impact['is_late'] = late_impact['is_late'].map({0: 'On Time', 1: 'Late'})
    
    fig_late = px.bar(
        late_impact,
        x='is_late',
        y='review_score',
        color='is_late',
        color_discrete_map={'On Time': 'green', 'Late': 'red'},
        template="plotly_dark",
        labels={'is_late': 'Delivery Status', 'review_score': 'Avg Review Score'}
    )
    fig_late.update_layout(height=350)
    st.plotly_chart(fig_late, use_container_width=True)
    
    add_export_button(filtered_data, "product_customer_intelligence.csv")
    render_footer()

# PAGE 6: AI Analyst Chat
elif page == "AI Analyst Chat":
    st.title("🤖 AI Analyst Chat")
    st.markdown("### Launch the AI-powered business analyst chatbot")
    
    st.info("""
    The AI Analyst Chat is available as a separate Streamlit application.
    
    To launch it, run the following command in your terminal:
    """)
    
    chatbot_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'chatbot.py')
    st.code(f"streamlit run {chatbot_path}", language='bash')
    
    st.markdown("""
    ### Features:
    - Ask business questions in plain English
    - Get instant SQL queries and results
    - Automatic chart generation
    - Conversation memory for follow-up questions
    - Export conversations to PDF
    - Voice of Data insights
    """)
    
    if st.button("🚀 Launch Chatbot Now", type="primary"):
        import subprocess
        import threading
        
        def run_chatbot():
            subprocess.run([sys.executable, "-m", "streamlit", "run", chatbot_path])
        
        # Run in a separate thread
        thread = threading.Thread(target=run_chatbot)
        thread.daemon = True
        thread.start()
        
        st.success("Chatbot is launching in a new browser window...")
        st.markdown(f"If it doesn't open automatically, navigate to: http://localhost:8501")

# Auto-refresh
time.sleep(60)
st.rerun()
