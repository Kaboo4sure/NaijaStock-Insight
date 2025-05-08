import streamlit as st
import pandas as pd
import sqlite3
import os

# Set page config
st.set_page_config(page_title="NaijaStock Insight", layout="wide")
st.title("📊 NaijaStock Insight Dashboard")

# Dynamically resolve DB path (works both locally and on Streamlit Cloud)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "naijastock.db")
conn = sqlite3.connect(DB_PATH)

# Load stock data
try:
    stock_df = pd.read_sql("SELECT * FROM stock_data", conn)
    st.subheader("📅 Recent Stock Prices")
    st.dataframe(stock_df.tail(10))
except Exception as e:
    st.error(f"❌ Failed to load stock data: {e}")
    conn.close()
    st.stop()

# Ticker filter
if 'ticker' in stock_df.columns:
    tickers = stock_df['ticker'].unique()
    selected_ticker = st.selectbox("Select a stock:", tickers)

    # Price trend
    filtered_price = stock_df[stock_df['ticker'] == selected_ticker]
    st.line_chart(filtered_price.set_index('date')['close'])

    # Load signals
    try:
        signals_df = pd.read_sql("SELECT * FROM weekly_signals", conn)
        filtered_signals = signals_df[signals_df['ticker'] == selected_ticker]

        st.subheader("📌 Weekly Trading Signals")

        if filtered_signals.empty:
            st.info(f"No trading signal this week for {selected_ticker}.")
        else:
            st.dataframe(filtered_signals.sort_values('date', ascending=False).reset_index(drop=True))

            # Show signal breakdown
            st.write("🔍 Signal Breakdown (Latest):")
            last = filtered_signals.sort_values('date', ascending=False).head(1)
            st.dataframe(last[[ 
                'date', 'RSI', 'macd', 'macdsignal',
                'five_day_return', 'volume_spike', 'signal_score'
            ]])
    except Exception as e:
        st.warning(f"⚠️ Signals table could not be loaded: {e}")
else:
    st.warning("⚠️ No 'ticker' column found in stock data.")

conn.close()
