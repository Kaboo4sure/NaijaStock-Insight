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

# Use 'ticker' as 'Company' name for display
stock_df = stock_df.rename(columns={'ticker': 'Company'})
signals_df = signals_df.rename(columns={'ticker': 'Company'})

# ------------------------------
# 📅 Recent Prices
# ------------------------------
st.subheader("📅 Recent Stock Prices")
st.dataframe(stock_df.tail(10))

# ------------------------------
# 📈 Weekly Gainers
# ------------------------------
st.subheader("📈 Weekly Gainers and Search")
latest_date = stock_df['date'].max()
week_ago = latest_date - pd.Timedelta(weeks=1)

latest = stock_df[stock_df['date'] == latest_date].groupby('Company').last()
previous = stock_df[stock_df['date'] <= week_ago].groupby('Company').first()

gain_df = ((latest['close'] - previous['close']) / previous['close']) * 100
gain_df = gain_df.reset_index()
gain_df.columns = ['Company', 'expected_gain']

search = st.text_input("🔍 Search companies", "")
filtered_gainers = gain_df[gain_df['Company'].str.contains(search, case=False)] if search else gain_df.copy()
st.dataframe(filtered_gainers.style.format({"expected_gain": "{:.2f}%"}))

# ------------------------------
# 📊 Trend Chart
# ------------------------------
st.subheader("📊 Trend Chart")
all_companies = sorted(stock_df['Company'].unique())
selected_companies = st.multiselect("Select companies to view trend", all_companies)

if selected_companies:
    trend_data = stock_df[stock_df['Company'].isin(selected_companies)]
    fig = px.line(trend_data, x='date', y='close', color='Company', title="Closing Price Trend")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Select one or more companies.")

# ------------------------------
# 📉 Percent Change Table
# ------------------------------
st.subheader("📉 % Change by Period")
period = st.selectbox("Select Period", ["1 Day", "1 Week", "1 Month"])
past_date = latest_date - pd.Timedelta(days=1 if period == "1 Day" else 7 if period == "1 Week" else 30)

current = stock_df[stock_df['date'] == latest_date].groupby("Company").last()
past = stock_df[stock_df['date'] <= past_date].groupby("Company").first()

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
    st.dataframe(buy_df[['Company', 'date', 'rsi', 'macd', 'five_day_return']].style.format({
        'rsi': '{:.2f}', 'macd': '{:.2f}', 'five_day_return': '{:.2f}%'
    }))
else:
    st.info("No BUY signals today.")

conn.close()
