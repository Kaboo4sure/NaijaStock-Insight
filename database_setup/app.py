import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from generate_signals import generate_signals
import os

# -------------------------------
# 🔧 Page Config
# -------------------------------
st.set_page_config(page_title="NaijaStock Insight", layout="wide")
st.title("📊 NaijaStock Insight Dashboard")

# -------------------------------
# 📥 Load Data from SQLite
# -------------------------------
@st.cache_data
def load_data():
    conn = sqlite3.connect("naijastock.db")
    df = pd.read_sql("SELECT * FROM stock_data", conn, parse_dates=["date"])
    conn.close()
    
    # Standardize column names
    df.columns = df.columns.str.lower()
    df = df.rename(columns={
        'ticker': 'company',
        'date': 'datetime',
        'close': 'close',
        'volume': 'volume'
    })
    
    return generate_signals(df)

df = load_data()
latest_date = df['datetime'].max()

# -------------------------------
# 🧮 Latest Stock Metrics
# -------------------------------
st.subheader("🧮 Latest Stock Metrics")
latest_df = df[df['datetime'] == latest_date].groupby('company').last().reset_index()

for idx, row in latest_df.iterrows():
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label=f"{row['company']} Price", value=f"₦{row['close']:.2f}")
    with col2:
        st.metric(label="Volume", value=f"{int(row['volume']):,}")
    with col3:
        st.metric(label="Signal Score", value=row['signal_score'])

st.markdown("---")

# -------------------------------
# 📈 Weekly Gainers Visualization
# -------------------------------
st.subheader("📈 Weekly Expected Gainers")
week_ago = latest_date - pd.Timedelta(weeks=1)

latest = df[df['datetime'] == latest_date].groupby('company').last()
previous = df[df['datetime'] <= week_ago].groupby('company').first()

gain_df = ((latest['close'] - previous['close']) / previous['close']) * 100
gain_df = gain_df.reset_index()
gain_df.columns = ['company', 'expected_gain']

threshold = st.selectbox("Select Gain Threshold", [10, 15, 20, 25])
filtered = gain_df[gain_df['expected_gain'] >= threshold]

if not filtered.empty:
    st.success(f"{len(filtered)} stock(s) expected to gain ≥ {threshold}% this week.")
    chart_type = st.radio("View as", ["Bar Chart", "Table"])

    if chart_type == "Bar Chart":
        fig = px.bar(filtered, x='company', y='expected_gain', color='company')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.dataframe(filtered.style.format({"expected_gain": "{:.2f}%"}))

    st.subheader("📊 Trend Line of Selected Stocks")
    selected = st.multiselect("Choose stock(s) to visualize", filtered['company'].tolist())
    if selected:
        trend_data = df[df['company'].isin(selected)]
        fig = px.line(trend_data, x='datetime', y='close', color='company', title="Trend of Selected Stocks")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No stocks meet the selected gain threshold.")

st.markdown("---")

# -------------------------------
# 📉 Percent Change Table
# -------------------------------
st.subheader("📉 % Price Change Table")

period_option = st.selectbox("Select time frame", ["1 Day", "1 Week", "1 Month"])
if period_option == "1 Day":
    past_date = latest_date - pd.Timedelta(days=1)
elif period_option == "1 Week":
    past_date = latest_date - pd.Timedelta(weeks=1)
else:
    past_date = latest_date - pd.Timedelta(days=30)

current = df[df['datetime'] == latest_date].groupby("company").last()
past = df[df['datetime'] <= past_date].groupby("company").first()

joined = current[['close']].join(past[['close']], lsuffix='_now', rsuffix='_past')
joined.dropna(inplace=True)
joined['% Change'] = ((joined['close_now'] - joined['close_past']) / joined['close_past']) * 100
joined = joined[['% Change']].reset_index()

st.dataframe(joined.style.format({"% Change": "{:.2f}%"}))

st.markdown("---")

# -------------------------------
# 🚦 Signal Score = 1 (Buy Signal)
# -------------------------------
st.subheader("🚦 BUY Signals (Score = 1)")
buy_df = df[(df['signal_score'] == 1) & (df['datetime'] == latest_date)]

if not buy_df.empty:
    st.success(f"{len(buy_df)} stock(s) triggered a BUY signal.")
    st.dataframe(buy_df[['company', 'datetime', 'close', 'rsi', 'macd', 'five_day_return']].style.format({
        'close': '₦{:.2f}', 'rsi': '{:.2f}', 'macd': '{:.2f}', 'five_day_return': '{:.2f}%'
    }))
else:
    st.info("No BUY signals generated today.")
