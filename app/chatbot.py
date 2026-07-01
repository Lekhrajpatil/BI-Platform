import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from groq import Groq
import json
import re
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Page configuration
st.set_page_config(
    page_title="AI Business Analyst",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for styling
st.markdown("""
<style>
    .chat-container {
        max-width: 1200px;
        margin: 0 auto;
    }
    .user-message {
        background-color: #1E88E5;
        color: white;
        padding: 15px 20px;
        border-radius: 20px 20px 5px 20px;
        margin: 10px 0 10px auto;
        max-width: 70%;
        text-align: right;
    }
    .ai-message {
        background-color: #161B22;
        color: #FAFAFA;
        padding: 15px 20px;
        border-radius: 20px 20px 20px 5px;
        margin: 10px auto 10px 0;
        max-width: 70%;
        border: 1px solid #30363D;
    }
    .typing-indicator {
        background-color: #161B22;
        color: #8B949E;
        padding: 15px 20px;
        border-radius: 20px;
        margin: 10px 0;
        border: 1px solid #30363D;
        font-style: italic;
    }
    .confidence-badge {
        display: inline-block;
        padding: 5px 15px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
        margin: 10px 0;
    }
    .confidence-high {
        background-color: #238636;
        color: white;
    }
    .confidence-medium {
        background-color: #d29922;
        color: white;
    }
    .confidence-low {
        background-color: #da3633;
        color: white;
    }
    .voice-of-data {
        background-color: #0D1117;
        border: 1px solid #30363D;
        border-radius: 10px;
        padding: 15px;
        margin: 15px 0;
    }
    .voice-of-data h4 {
        color: #58A6FF;
        margin-top: 0;
    }
    .footer {
        text-align: center;
        padding: 20px;
        color: #8B949E;
        font-size: 12px;
        margin-top: 40px;
    }
    .example-button {
        background-color: #238636;
        color: white;
        border: none;
        padding: 10px 15px;
        border-radius: 8px;
        margin: 5px;
        cursor: pointer;
        font-size: 13px;
    }
    .example-button:hover {
        background-color: #2EA043;
    }
</style>
""", unsafe_allow_html=True)

# System prompt for AI
SYSTEM_PROMPT = """You are a senior business analyst working with an e-commerce company. You have access to this PostgreSQL database:

Tables:
- fact_orders (order_id, customer_id, product_id, revenue, delivery_days, is_late, review_score, order_date)
- dim_customers (customer_id, city, state)
- dim_products (product_id, category)

When user asks a business question always return ONLY this exact JSON format, nothing else, no markdown, no backticks:
{
  "sql": "your PostgreSQL query here",
  "explanation": "what this query finds",
  "chart_type": "bar or line or pie or none",
  "chart_x": "column name for x axis",
  "chart_y": "column name for y axis",
  "business_insight": "2-3 sentence professional insight",
  "key_finding": "most interesting thing in data",
  "recommendation": "what business should do",
  "confidence": "High or Medium or Low"
}"""

# Initialize conversation history
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

def call_ai(user_question, conversation_history):
    
    system_prompt = """You are a senior business analyst 
    working with an e-commerce company. You have access 
    to this PostgreSQL database:

    Tables:
    - fact_orders (order_id, customer_id, product_id, 
      revenue, delivery_days, is_late, review_score, 
      order_date)
    - dim_customers (customer_id, city, state)
    - dim_products (product_id, category)

    Always return ONLY this exact JSON format, 
    no markdown, no backticks, nothing else:
    {
      "sql": "your PostgreSQL query here",
      "explanation": "what this query finds",
      "chart_type": "bar or line or pie or none",
      "chart_x": "column name for x axis",
      "chart_y": "column name for y axis",
      "business_insight": "2-3 sentence professional insight",
      "key_finding": "most interesting thing in data",
      "recommendation": "what business should do",
      "confidence": "High or Medium or Low"
    }"""

    messages = [{"role": "system", "content": system_prompt}]
    
    for msg in conversation_history[-5:]:
        messages.append(msg)
    
    messages.append({
        "role": "user", 
        "content": user_question
    })

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.1,
        max_tokens=1024
    )
    
    return response.choices[0].message.content

# Safe JSON parsing function
def parse_ai_response(raw_response):
    try:
        # Remove markdown backticks if present
        clean = raw_response.strip()
        clean = re.sub(r'^```json', '', clean)
        clean = re.sub(r'^```', '', clean)
        clean = re.sub(r'```$', '', clean)
        clean = clean.strip()
        return json.loads(clean)
    except Exception as e:
        return {
            "sql": None,
            "explanation": "Could not parse response",
            "chart_type": "none",
            "chart_x": "",
            "chart_y": "",
            "business_insight": raw_response,
            "key_finding": "",
            "recommendation": "",
            "confidence": "Low"
        }

# Safe SQL execution function
def run_sql(sql_query):
    try:
        engine = create_engine(
            f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )
        with engine.connect() as conn:
            result = pd.read_sql(text(sql_query), conn)
        return result, None
    except Exception as e:
        return None, str(e)

# Main chat processing function
def process_question(user_question, conversation_history):
    # Show loading message
    with st.spinner("Analyzing your data..."):
        raw_response = call_ai(
            user_question, 
            conversation_history
        )
        
        # Parse response
        parsed = parse_ai_response(raw_response)
        
        # Run SQL if exists
        df = None
        error = None
        if parsed["sql"]:
            df, error = run_sql(parsed["sql"])
            
            # Retry once if SQL fails
            if error:
                retry_question = f"""
                This SQL failed: {parsed["sql"]}
                Error: {error}
                Fix the SQL and try again for: {user_question}
                """
                raw_response2 = call_ai(
                    retry_question, 
                    conversation_history
                )
                parsed = parse_ai_response(raw_response2)
                if parsed["sql"]:
                    df, error = run_sql(parsed["sql"])
        
        return parsed, df, error

# Function to create chart
def create_chart(result_df, chart_type, chart_x, chart_y):
    if result_df is None or len(result_df) == 0 or chart_type == "none":
        return None
    
    try:
        if chart_type == "bar":
            if chart_x and chart_y and chart_x in result_df.columns and chart_y in result_df.columns:
                fig = px.bar(
                    result_df,
                    x=chart_x,
                    y=chart_y,
                    template="plotly_dark",
                    color=chart_y,
                    color_continuous_scale='Viridis'
                )
            else:
                # Auto-select columns
                numeric_cols = result_df.select_dtypes(include=[np.number]).columns
                categorical_cols = result_df.select_dtypes(include=['object']).columns
                if len(categorical_cols) > 0 and len(numeric_cols) > 0:
                    fig = px.bar(
                        result_df,
                        x=categorical_cols[0],
                        y=numeric_cols[0],
                        template="plotly_dark",
                        color=numeric_cols[0],
                        color_continuous_scale='Viridis'
                    )
                else:
                    return None
                    
        elif chart_type == "line":
            if chart_x and chart_y and chart_x in result_df.columns and chart_y in result_df.columns:
                fig = px.line(
                    result_df,
                    x=chart_x,
                    y=chart_y,
                    template="plotly_dark",
                    markers=True
                )
            else:
                numeric_cols = result_df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    fig = px.line(
                        result_df,
                        y=numeric_cols[0],
                        template="plotly_dark",
                        markers=True
                    )
                else:
                    return None
                    
        elif chart_type == "pie":
            if chart_x and chart_y and chart_x in result_df.columns and chart_y in result_df.columns:
                fig = px.pie(
                    result_df,
                    names=chart_x,
                    values=chart_y,
                    template="plotly_dark"
                )
            else:
                categorical_cols = result_df.select_dtypes(include=['object']).columns
                numeric_cols = result_df.select_dtypes(include=[np.number]).columns
                if len(categorical_cols) > 0 and len(numeric_cols) > 0:
                    fig = px.pie(
                        result_df,
                        names=categorical_cols[0],
                        values=numeric_cols[0],
                        template="plotly_dark"
                    )
                else:
                    return None
        else:
            return None
        
        fig.update_layout(height=400)
        return fig
        
    except Exception as e:
        st.error(f"Error creating chart: {str(e)}")
        return None

# Main UI
st.title("🤖 AI Business Analyst")
st.markdown("### Ask me anything about your e-commerce business")

# Example question buttons
example_questions = [
    "What are my top 5 revenue products?",
    "Which state has highest late delivery rate?",
    "Show me monthly revenue trend",
    "Which customers are at highest churn risk?",
    "What is average review score by category?",
    "Compare on-time vs late delivery review scores",
    "Who are my top 10 customers by spending?",
    "What was best and worst month for revenue?"
]

st.markdown("#### Quick Questions:")
cols = st.columns(4)
for idx, question in enumerate(example_questions):
    with cols[idx % 4]:
        if st.button(question, key=f"example_{idx}", use_container_width=True):
            st.session_state.user_input = question

# Chat interface
chat_container = st.container()

# Display conversation history
with chat_container:
    for item in st.session_state.conversation_history:
        # User message
        st.markdown(f"""
        <div class="user-message">
            {item['user']}
        </div>
        """, unsafe_allow_html=True)
        
        # AI message
        st.markdown(f"""
        <div class="ai-message">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span>🤖</span>
                <strong>AI Analyst</strong>
            </div>
            {item['ai']}
        </div>
        """, unsafe_allow_html=True)
        
        # Show additional details if available
        if 'sql' in item and item['sql']:
            with st.expander("View SQL Query"):
                st.code(item['sql'], language='sql')
        
        if 'result_df' in item and item['result_df'] is not None:
            st.dataframe(item['result_df'], use_container_width=True)
        
        if 'chart' in item and item['chart'] is not None:
            st.plotly_chart(item['chart'], use_container_width=True)
        
        if 'confidence' in item:
            confidence_class = f"confidence-{item['confidence'].lower()}"
            st.markdown(f"""
            <div class="confidence-badge {confidence_class}">
                Confidence: {item['confidence']}
            </div>
            """, unsafe_allow_html=True)
        
        if 'key_finding' in item or 'recommendation' in item:
            st.markdown(f"""
            <div class="voice-of-data">
                <h4>📊 Voice of Data</h4>
                <p><strong>Key Finding:</strong> {item.get('key_finding', '')}</p>
                <p><strong>Recommendation:</strong> {item.get('recommendation', '')}</p>
            </div>
            """, unsafe_allow_html=True)

# User input
user_input = st.text_input(
    "Type your business question here...",
    value=st.session_state.get('user_input', ''),
    key='chat_input'
)

# Send button
col1, col2 = st.columns([6, 1])
with col2:
    send_button = st.button("Send", type="primary", use_container_width=True)

# Process user input
if send_button and user_input:
    # Clear the input
    st.session_state.user_input = ""
    
    # Process question
    parsed, df, error = process_question(user_input, st.session_state.conversation_history)
    
    if error:
        st.error(f"SQL Error: {error}")
    elif parsed:
        # Create chart
        chart = create_chart(df, parsed["chart_type"], parsed["chart_x"], parsed["chart_y"])
        
        # Add to conversation history
        conversation_item = {
            'user': user_input,
            'ai': parsed["business_insight"],
            'sql': parsed["sql"],
            'result_df': df,
            'chart': chart,
            'confidence': parsed["confidence"],
            'key_finding': parsed["key_finding"],
            'recommendation': parsed["recommendation"]
        }
        st.session_state.conversation_history.append(conversation_item)
        
        # Keep only last 10 conversations
        if len(st.session_state.conversation_history) > 10:
            st.session_state.conversation_history = st.session_state.conversation_history[-10:]
        
        st.rerun()
    else:
        st.error("Failed to get a response. Please try again.")

# Footer
st.markdown("""
<div class="footer">
    Powered by Groq · PostgreSQL · Streamlit
</div>
""", unsafe_allow_html=True)
