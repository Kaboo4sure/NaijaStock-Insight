import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px

# Set page config
st.set_page_config(page_title="NaijaStock Insight", layout="wide")
st.title("📊 NaijaStock Insight Dashboard")

# Resolve DB path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "naijastock.db")

# Load data
try:
    conn = sqlite3.connect(DB_PATH)
    stock_df = pd.read_sql("SELECT * FROM stock_data", conn)
    signals_df = pd.read_sql("SELECT * FROM weekly_signals", conn)
except Exception as e:
    st.error(f"❌ Could not load database: {e}")
    st.stop()

# Normalize and clean
stock_df.columns = stock_df.columns.str.lower()
signals_df.columns = signals_df.columns.str.lower()
stock_df['date'] = pd.to_datetime(stock_df['date'], errors='coerce')
signals_df['date'] = pd.to_datetime(signals_df['date'], errors='coerce')

# Fallback if company_name not available
if 'company_name' not in stock_df.columns:
    stock_df['company_name'] = stock_df['ticker']
if 'company_name' not in signals_df.columns and 'ticker' in signals_df.columns:
    signals_df = pd.merge(signals_df, stock_df[['ticker', 'company_name']].drop_duplicates(), how='left', on='ticker')

# ------------------------------
# 📅 Recent Prices
# ------------------------------
st.subheader("📅 Recent Stock Prices")
st.dataframe(stock_df.tail(10)[['date', 'company_name', 'ticker', 'close', 'volume']])

# ------------------------------
# 📈 Weekly Gainers
# ------------------------------
st.subheader("📈 Weekly Gainers and Search")
latest_date = stock_df['date'].max()
week_ago = latest_date - pd.Timedelta(weeks=1)

latest = stock_df[stock_df['date'] == latest_date].groupby('company_name').last()
previous = stock_df[stock_df['date'] <= week_ago].groupby('company_name').first()

gain_df = ((latest['close'] - previous['close']) / previous['close']) * 100
gain_df = gain_df.reset_index()
gain_df.columns = ['company_name', 'expected_gain']

search = st.text_input("🔍 Search companies", "")
filtered_gainers = gain_df[gain_df['company_name'].str.contains(search, case=False)] if search else gain_df.copy()
st.dataframe(filtered_gainers.style.format({"expected_gain": "{:.2f}%"}))

# ------------------------------
# 📊 Trend Chart
# ------------------------------
st.subheader("📊 Trend Chart")
all_companies = sorted(stock_df['company_name'].dropna().unique())
selected_companies = st.multiselect("Select companies to view trend", all_companies)

if selected_companies:
    trend_data = stock_df[stock_df['company_name'].isin(selected_companies)]
    fig = px.line(trend_data, x='date', y='close', color='company_name', title="Closing Price Trend")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Select one or more companies.")

# ------------------------------
# 📉 Percent Change Table
# ------------------------------
st.subheader("📉 % Change by Period")
period = st.selectbox("Select Period", ["1 Day", "1 Week", "1 Month"])
past_date = latest_date - pd.Timedelta(days=1 if period == "1 Day" else 7 if period == "1 Week" else 30)

current = stock_df[stock_df['date'] == latest_date].groupby("company_name").last()
past = stock_df[stock_df['date'] <= past_date].groupby("company_name").first()

joined = current[['close']].join(past[['close']], lsuffix='_now', rsuffix='_past')
joined.dropna(inplace=True)
joined['% Change'] = ((joined['close_now'] - joined['close_past']) / joined['close_past']) * 100
joined = joined[['% Change']].reset_index()
st.dataframe(joined.style.format({"% Change": "{:.2f}%"}))

# ------------------------------
# 📌 BUY Signal Summary
# ------------------------------
st.subheader("🚦 BUY Signal Summary")
buy_df = signals_df[(signals_df['signal_score'] == 1) & (signals_df['date'] == signals_df['date'].max())]

if not buy_df.empty:
    st.success(f"{len(buy_df)} stock(s) triggered a BUY signal.")
    st.dataframe(buy_df[['company_name', 'date', 'rsi', 'macd', 'five_day_return']].style.format({
        'rsi': '{:.2f}', 'macd': '{:.2f}', 'five_day_return': '{:.2f}%'
    }))
else:
    st.info("No BUY signals today.")

conn.close()
