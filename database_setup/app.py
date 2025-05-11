import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px

# --- App Config ---
st.set_page_config(page_title="NaijaStock Insight", layout="wide")
st.title("📊 NaijaStock Insight Dashboard")

# --- Connect to Database ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "naijastock.db")

try:
    conn = sqlite3.connect(DB_PATH)
    stock_df = pd.read_sql("SELECT * FROM stock_data", conn)
    signal_df = pd.read_sql("SELECT * FROM weekly_signals", conn)
except Exception as e:
    st.error(f"❌ Could not load database: {e}")
    st.stop()

# --- Clean Data ---
stock_df.columns = stock_df.columns.str.lower()
signal_df.columns = signal_df.columns.str.lower()
stock_df['date'] = pd.to_datetime(stock_df['date'], errors='coerce')
signal_df['date'] = pd.to_datetime(signal_df['date'], errors='coerce')

if 'company_name' not in stock_df.columns:
    stock_df['company_name'] = stock_df['ticker']

if 'company_name' not in signal_df.columns and 'ticker' in signal_df.columns:
    signal_df = pd.merge(signal_df, stock_df[['ticker', 'company_name']].drop_duplicates(), on='ticker', how='left')

# --- Sidebar Filters ---
st.sidebar.header("📂 Filters")
all_companies = sorted(stock_df['company_name'].dropna().unique())
selected_companies = st.sidebar.multiselect("Select Companies", all_companies, default=all_companies[:5])
selected_period = st.sidebar.selectbox("Period for % Change", ["1 Day", "1 Week", "1 Month"])
show_only_buy = st.sidebar.checkbox("✅ Show Only BUY Signals", value=True)

# --- KPIs ---
latest_date = stock_df['date'].max()
week_ago = latest_date - pd.Timedelta(weeks=1)

kpi1 = signal_df[(signal_df['signal_score'] == 1) & (signal_df['date'] == latest_date)]
kpi2 = stock_df[stock_df['date'] == latest_date].groupby("company_name")['close'].mean().idxmax()

col1, col2 = st.columns(2)
col1.metric("📈 BUY Signals Today", len(kpi1))
col2.metric("🚀 Top Gainer (by Price)", kpi2)

# --- Recent Prices Table ---
st.subheader("📅 Latest Prices")
recent = stock_df[stock_df['date'] == latest_date]
st.dataframe(recent[['company_name', 'ticker', 'close', 'volume', 'date']].sort_values(by='close', ascending=False))

# --- Weekly Gainers ---
st.subheader("📈 Weekly % Gain")
latest = stock_df[stock_df['date'] == latest_date].groupby('company_name').last()
previous = stock_df[stock_df['date'] <= week_ago].groupby('company_name').first()
gain_df = ((latest['close'] - previous['close']) / previous['close']) * 100
gain_df = gain_df.reset_index().rename(columns={0: 'expected_gain', 'close': 'expected_gain'})
gain_df.columns = ['company_name', 'expected_gain']
gain_df = gain_df[gain_df['company_name'].isin(selected_companies)]

st.dataframe(gain_df.style.format({"expected_gain": "{:.2f}%"}))

# --- Trend Chart ---
st.subheader("📊 Price Trend")
if selected_companies:
    trend_data = stock_df[stock_df['company_name'].isin(selected_companies)]
    fig = px.line(trend_data, x='date', y='close', color='company_name', title="Closing Price Over Time")
    st.plotly_chart(fig, use_container_width=True)

# --- % Change Table ---
st.subheader("📉 % Price Change")

days_back = 1 if selected_period == "1 Day" else 7 if selected_period == "1 Week" else 30
past_date = latest_date - pd.Timedelta(days=days_back)

current = stock_df[stock_df['date'] == latest_date].groupby("company_name").last()
past = stock_df[stock_df['date'] <= past_date].groupby("company_name").first()
joined = current[['close']].join(past[['close']], lsuffix='_now', rsuffix='_past')
joined.dropna(inplace=True)
joined['% Change'] = ((joined['close_now'] - joined['close_past']) / joined['close_past']) * 100
joined = joined.reset_index()
joined = joined[joined['company_name'].isin(selected_companies)]

st.dataframe(joined[['company_name', '% Change']].style.format({"% Change": "{:.2f}%"}))

# --- Signal Table ---
st.subheader("🚦 Signal Summary")

filtered_signals = signal_df[signal_df['company_name'].isin(selected_companies)]
filtered_signals = filtered_signals[filtered_signals['date'] == latest_date]

if show_only_buy:
    filtered_signals = filtered_signals[filtered_signals['signal_score'] == 1]

if not filtered_signals.empty:
    st.dataframe(filtered_signals[['company_name', 'date', 'rsi', 'macd', 'five_day_return', 'signal_score']].style.format({
        'rsi': '{:.2f}', 'macd': '{:.2f}', 'five_day_return': '{:.2f}%', 'signal_score': '{:.0f}'
    }))
    csv = filtered_signals.to_csv(index=False)
    st.download_button("⬇️ Download Signals CSV", csv, "filtered_signals.csv", "text/csv")
else:
    st.info("No signals match your criteria.")

# --- Cleanup ---
conn.close()
