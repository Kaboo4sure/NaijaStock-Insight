import pandas as pd
import pandas_ta as ta
import sqlite3

def generate_signals(df):
    df.columns = df.columns.str.lower()
    required_cols = ['date', 'close', 'volume']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    df = df.sort_values(by=['ticker', 'date']) if 'ticker' in df.columns else df.sort_values(by='date')

    df['five_day_return'] = df['close'].pct_change(5) * 100
    df['RSI'] = ta.rsi(df['close'], length=14)

    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    if macd is not None:
        df['macd'] = macd['MACD_12_26_9']
        df['macdsignal'] = macd['MACDs_12_26_9']
        df['macdhist'] = macd['MACDh_12_26_9']
    else:
        df['macd'] = df['macdsignal'] = df['macdhist'] = float('nan')

    df['twenty_day_avg_volume'] = df['volume'].rolling(window=20).mean()
    df['volume_spike'] = df['volume'] > df['twenty_day_avg_volume']

    df['signal_score'] = 0
    df.loc[
        (df['five_day_return'] > 0) &
        (df['RSI'] < 70) &
        (df['macd'] > df['macdsignal']) &
        (df['volume_spike'] == True),
        'signal_score'
    ] = 1

    df.reset_index(drop=True, inplace=True)

    if 'ticker' in df.columns:
        print(df[['date', 'ticker', 'signal_score']].tail())
    else:
        print(df[['date', 'signal_score']].tail())

    return df


# 🔁 NEW: Load from stock_data, generate signals, save to weekly_signals
if __name__ == "__main__":
    db_path = "naijastock.db"
    conn = sqlite3.connect(db_path)

    try:
        stock_df = pd.read_sql("SELECT * FROM stock_data", conn)
        signal_df = generate_signals(stock_df)
        signal_df.to_sql("weekly_signals", conn, if_exists="replace", index=False)
        print(f"✅ weekly_signals table created with {len(signal_df)} rows.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()
