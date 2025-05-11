import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
import plotly.graph_objects as go

# --- App Config ---
st.set_page_config(page_title="NaijaStock Insight", layout="wide")

# --- Dark Mode Toggle ---
theme = st.sidebar.radio("Theme Mode", ["Light", "Dark"])
if theme == "Dark":
    st.markdown("""
        <style>
        body, .stApp { background-color: #0e1117; color: white; }
        .css-1d391kg { color: white; }
        </style>
    """, unsafe_allow_html=True)

st.title("📊 NaijaStock Insight Dashboard")

# --- Load Database ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "naijastock.db")

try:
    conn = sqlite3.connect(DB_PATH)
    stock_df = pd.read_sql("SELECT * FROM stock_data", conn)
    signal_df = pd.read_sql("SELECT * FROM weekly_signals", conn)
except Exception as e:
    signal_df = pd.DataFrame()
    st.warning("Note: Signals will be shown once weekly_signals table is available.")

# --- Clean Data ---
stock_df.columns = stock_df.columns.str.lower()
stock_df['date'] = pd.to_datetime(stock_df['date'], errors='coerce')

if 'company_name' not in stock_df.columns:
    stock_df['company_name'] = stock_df['ticker']

if not signal_df.empty:
    signal_df.columns = signal_df.columns.str.lower()
    signal_df['date'] = pd.to_datetime(signal_df['date'], errors='coerce')
    if 'company_name' not in signal_df.columns and 'ticker' in signal_df.columns:
        signal_df = pd.merge(signal_df, stock_df[['ticker', 'company_name']].drop_duplicates(), on='ticker', how='left')

# --- Sidebar Filters ---
st.sidebar.header("📂 Filters")
all_companies = sorted(stock_df['company_name'].dropna().unique())
selected_companies = st.sidebar.multiselect("Select Companies", all_companies, default=all_companies[:5])
chart_type = st.sidebar.radio("Chart Type", ["Line Chart", "Candlestick"])
show_only_buy = st.sidebar.checkbox("✅ Show Only BUY Signals", value=True)
selected_period = st.sidebar.selectbox("Period for % Change", ["1 Day", "1 Week", "1 Month"])

# --- KPIs ---
latest_date = stock_df['date'].max()
col1, col2 = st.columns(2)
col1.metric("📅 Latest Date", latest_date.strftime('%Y-%m-%d'))

if not signal_df.empty:
    latest_signals = signal_df[signal_df['date'] == latest_date]
    col2.metric("🚦 BUY Signals Today", int((latest_signals['signal_score'] == 1).sum()))

# --- Trend Chart ---
st.subheader("📈 Price Trend")
if selected_companies:
    filtered = stock_df[stock_df['company_name'].isin(selected_companies)]
    if chart_type == "Line Chart":
        fig = px.line(filtered, x='date', y='close', color='company_name')
        st.plotly_chart(fig, use_container_width=True)
    else:
        for company in selected_companies:
            sub = filtered[filtered['company_name'] == company]
            fig = go.Figure(data=[go.Candlestick(x=sub['date'],
                        open=sub['open'], high=sub['high'],
                        low=sub['low'], close=sub['close'])])
            fig.update_layout(title=f"Candlestick - {company}", xaxis_title='Date', yaxis_title='Price')
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Please select at least one company.")

# --- Percent Change Table ---
st.subheader("📉 % Price Change")
days_back = 1 if selected_period == "1 Day" else 7 if selected_period == "1 Week" else 30
past_date = latest_date - pd.Timedelta(days=days_back)
current = stock_df[stock_df['date'] == latest_date].groupby("company_name").last()
past = stock_df[stock_df['date'] <= past_date].groupby("company_name").first()
joined = current[['close']].join(past[['close']], lsuffix='_now', rsuffix='_past')
joined.dropna(inplace=True)
joined['% Change'] = ((joined['close_now'] - joined['close_past']) / joined['close_past']) * 100
joined = joined[['% Change']].reset_index()
if selected_companies:
    joined = joined[joined['company_name'].isin(selected_companies)]
st.dataframe(joined.style.format({"% Change": "{:.2f}%"}))

# --- BUY Signals Table ---
if not signal_df.empty:
    st.subheader("🚦 Signal Table")
    recent_signals = signal_df[signal_df['date'] == latest_date]
    if selected_companies:
        recent_signals = recent_signals[recent_signals['company_name'].isin(selected_companies)]
    if show_only_buy:
        recent_signals = recent_signals[recent_signals['signal_score'] == 1]

    if not recent_signals.empty:
        st.dataframe(recent_signals[['company_name', 'date', 'rsi', 'macd', 'five_day_return', 'signal_score']]
                     .style.format({
                         'rsi': '{:.2f}', 'macd': '{:.2f}', 'five_day_return': '{:.2f}%', 'signal_score': '{:.0f}'
                     }))
        csv = recent_signals.to_csv(index=False)
        st.download_button("⬇️ Download Signal Data", csv, "signals.csv", "text/csv")
    else:
        st.info("No signals to display.")

# --- Aggregated Insight (Optional Sector-Level) ---
if not signal_df.empty:
    st.subheader("📊 Average RSI by Company")
    avg_rsi = signal_df.groupby("company_name")['rsi'].mean().reset_index().dropna()
    if selected_companies:
        avg_rsi = avg_rsi[avg_rsi['company_name'].isin(selected_companies)]
    fig = px.bar(avg_rsi.sort_values(by='rsi'), x='company_name', y='rsi', title="Avg RSI by Company")
    st.plotly_chart(fig, use_container_width=True)

conn.close()
