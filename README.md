# 🚀 E-Commerce BI Platform
### End-to-End AI-Powered Business Intelligence System

![Python](https://img.shields.io/badge/Python-3.10-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![XGBoost](https://img.shields.io/badge/XGBoost-ML-green)
![Claude AI](https://img.shields.io/badge/Claude-AI%20Chatbot-purple)

## 📌 Project Overview
A full end-to-end business intelligence platform built on 
100,000+ real e-commerce orders. Combines SQL data warehouse, 
machine learning models, interactive dashboard, and an AI chatbot 
that answers business questions in plain English.

## 🎯 Business Problems Solved
- Which customers are about to leave? (Churn Prediction)
- What will revenue look like next 6 months? (Sales Forecast)
- Which products and states drive most revenue? (BI Dashboard)
- How can non-technical teams access data insights? (AI Chatbot)

## 📊 Key Results
- Churn prediction model: 88% accuracy
- Sales forecast: within 8% of actual revenue
- 100,000+ orders analyzed
- 5-page interactive dashboard
- AI chatbot answers in under 3 seconds

 🛠️ Tech Stack
| Layer | Tools |
| Data Cleaning | Python, Pandas, NumPy |
| Database | PostgreSQL, SQL, SQLAlchemy |
| Machine Learning | Scikit-learn, XGBoost, Prophet |
| Dashboard | Streamlit, Plotly |
| AI Chatbot | Claude API (Anthropic) |
| Deployment | Streamlit Cloud |

 📁 Project Structure
```
BI-Platform/
├── app/
│   ├── dashboard.py
│   ├── chatbot.py
│   └── config.py
├── data/
│   ├── raw/          
│   └── cleaned/
│       ├── master_data.csv
│       └── sales_forecast.csv
├── models/
│   └── churn_model.pkl
├── notebooks/
│   ├── 01_data_cleaning.ipynb
│   ├── 02_sql_analysis.ipynb
│   └── 03_ml_models.ipynb
├── images/
│   ├── churn_confusion_matrix.png
│   └── sales_forecast.png
├── sql/
│   ├── schema.sql
│   └── load_data.py
├── .streamlit/
│   └── config.toml
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

 🚀 How to Run Locally
1. Clone this repo
2. pip install -r requirements.txt
3. Copy .env.example to .env and add your API keys
4. Run: streamlit run app/dashboard.py

## 💡 What I Learned
- Built a real SQL star schema data warehouse from scratch
- Handled severely imbalanced churn dataset using RFM features
- Connected AI language model to live database for natural language queries
- Deployed a full multi-page data application to cloud

## 📬 Contact
Built by Lekhraj Patil | https://www.linkedin.com/in/lekhraj-patil-853595317/ | patillekhraj93@gmail.com
