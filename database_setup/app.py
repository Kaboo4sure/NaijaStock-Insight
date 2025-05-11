import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px

# Set page config
st.set_page_config(page_title="NaijaStock Insight", layout="wide")
st.title("📊 NaijaStock Insight Dashboard")

# Dynamically resolve DB path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "naijastock.db")

# Load stock data
try:
    conn = sqlite3.connect(DB_PATH)
    stock_df = pd.read_sql("SELECT * FROM stock_data", conn)
    signals_df = pd.read_sql("SELECT * FROM weekly_signals", conn)
except Exception as e:
    st.error(f"❌ Could not load database: {e}")
    st.stop()

# Normalize column names
stock_df.columns = stock_df.columns.str.lower()
signals_df.columns = signals_df.columns.str.lower()

# Ensure date columns are datetime
stock_df['date'] = pd.to_datetime(stock_df['date'], errors='coerce')
signals_df['date'] = pd.to_datetime(signals_df['date'], errors='coerce')

# Recent Stock Prices Table
st.subheader("📅 Recent Stock Prices")
st.dataframe(stock_df.tail(10))

# Select ticker
if 'ticker' in stock_df.columns:
    tickers = stock_df['ticker'].unique()
    selected_ticker = st.selectbox("Select a stock:", tickers)

    filtered_price = stock_df[stock_df['ticker'] == selected_ticker]
    st.line_chart(filtered_price.set_index('date')['close'])

    st.subheader("📌 Weekly Trading Signals")
    filtered_signals = signals_df[signals_df['ticker'] == selected_ticker]

    if filtered_signals.empty:
        st.info(f"No trading signal this week for {selected_ticker}.")
    else:
        latest_signals = filtered_signals.sort_values('date')

        col1, col2 = st.columns(2)
        with col1:
            show_only_buy = st.checkbox("✅ Show only BUY signals (score = 1)")
        with col2:
            min_date = latest_signals['date'].min()
            max_date = latest_signals['date'].max()
            date_range = st.date_input("📅 Select Date Range", [min_date, max_date])

        if show_only_buy:
            latest_signals = latest_signals[latest_signals['signal_score'] == 1]

        if len(date_range) == 2:
            start_date, end_date = date_range
            latest_signals = latest_signals[
                (latest_signals['date'] >= pd.to_datetime(start_date)) &
                (latest_signals['date'] <= pd.to_datetime(end_date))
            ]

        if latest_signals.empty:
            st.info(f"No signals match your filter for {selected_ticker}.")
        else:
            st.dataframe(latest_signals.tail(10)[[
                'date', 'rsi', 'macd', 'macdsignal',
                'five_day_return', 'volume_spike', 'signal_score'
            ]])

            csv = latest_signals.to_csv(index=False)
            st.download_button(
                label="⬇️ Download Filtered Signals as CSV",
                data=csv,
                file_name=f"{selected_ticker}_signals.csv",
                mime='text/csv'
            )

            st.write("📉 RSI Trend")
            st.line_chart(latest_signals.set_index('date')['rsi'])

            st.write("📉 MACD vs Signal Line")
            st.line_chart(latest_signals.set_index('date')[['macd', 'macdsignal']])

            st.write("🔁 Volume Spike (1 = True, 0 = False)")
            vol_df = latest_signals[['date', 'volume_spike']].copy()
            vol_df['volume_spike'] = vol_df['volume_spike'].astype(int)
            vol_df = vol_df.set_index('date')
            st.bar_chart(vol_df)

else:
    st.warning("⚠️ No 'ticker' column found in stock data.")

st.markdown("---")

# 📊 Weekly Gain Threshold Filter
st.subheader("📈 Weekly Expected Gainers")
latest_date = stock_df['date'].max()
week_ago = latest_date - pd.Timedelta(weeks=1)

latest = stock_df[stock_df['date'] == latest_date].groupby('ticker').last()
previous = stock_df[stock_df['date'] <= week_ago].groupby('ticker').first()

gain_df = ((latest['close'] - previous['close']) / previous['close']) * 100
gain_df = gain_df.reset_index().rename(columns={0: 'expected_gain'})
gain_df.columns = ['ticker', 'expected_gain']

threshold = st.selectbox("📊 Select Gain Threshold", [10, 15, 20, 25])
filtered = gain_df[gain_df['expected_gain'] >= threshold]

if not filtered.empty:
    st.success(f"{len(filtered)} stock(s) expected to gain ≥ {threshold}% this week.")
    chart_type = st.radio("View chart as", ["Bar Chart", "Table"])

    if chart_type == "Bar Chart":
        fig = px.bar(filtered, x='ticker', y='expected_gain', color='ticker',
                     color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.dataframe(filtered.style.format({"expected_gain": "{:.2f}%"}))

    st.subheader("📈 Trend Line for Selected Stocks")
    selected = st.multiselect("Select stocks to view trend", filtered['ticker'].tolist())
    if selected:
        trend_data = stock_df[stock_df['ticker'].isin(selected)]
        fig = px.line(trend_data, x='date', y='close', color='ticker', title="Price Trend")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No stocks meet the selected gain threshold.")

# 🚦 Signal Summary
st.subheader("🚦 BUY Signal Summary (Signal Score = 1)")
today_signals = signals_df[(signals_df['signal_score'] == 1) & (signals_df['date'] == signals_df['date'].max())]

if not today_signals.empty:
    st.success(f"{len(today_signals)} stocks triggered a BUY signal today.")
    st.dataframe(today_signals[['ticker', 'date', 'rsi', 'macd', 'five_day_return']].style.format({
        'rsi': '{:.2f}', 'macd': '{:.2f}', 'five_day_return': '{:.2f}%'
    }))
else:
    st.info("No BUY signals today.")

conn.close()
