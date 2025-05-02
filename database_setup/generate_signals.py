import sqlite3
import pandas as pd
import pandas_ta as ta  # <-- Using pandas-ta instead of ta-lib

# Load stock data from SQLite
def load_stock_data():
    conn = sqlite3.connect('naijastock.db')
    df = pd.read_sql("SELECT * FROM stock_data", conn, parse_dates=["date"])
    conn.close()
    return df.dropna(subset=['date'])

# Generate trading signals
def generate_signals(df):
    df = df.sort_values('date')

    # Calculate indicators
    df['five_day_return'] = df['close'].pct_change(5) * 100
    df['RSI'] = ta.rsi(df['close'], length=14)
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    df['macd'] = macd['MACD_12_26_9']
    df['macdsignal'] = macd['MACDs_12_26_9']
    df['macdhist'] = macd['MACDh_12_26_9']
    df['twenty_day_avg_volume'] = df['volume'].rolling(20).mean()
    df['volume_spike'] = df['volume'] > df['twenty_day_avg_volume']

    # Signal logic
    df['signal_score'] = 0
    df.loc[
        (df['five_day_return'] > 0) &
        (df['RSI'] < 70) &
        (df['macd'] > df['macdsignal']) &
        (df['volume_spike']),
        'signal_score'
    ] = 1

    return df

# Save signals to DB
def save_signals_to_db(df):
    conn = sqlite3.connect('naijastock.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weekly_signals (
            date TEXT,
            ticker TEXT,
            five_day_return REAL,
            RSI REAL,
            macd REAL,
            macdsignal REAL,
            volume_spike BOOLEAN,
            signal_score INTEGER
        )
    ''')
    for _, row in df.iterrows():
        cursor.execute('''
            INSERT INTO weekly_signals 
            (date, ticker, five_day_return, RSI, macd, macdsignal, volume_spike, signal_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['date'], row['ticker'], row['five_day_return'], row['RSI'],
            row['macd'], row['macdsignal'], row['volume_spike'], row['signal_score']
        ))
    conn.commit()
    conn.close()
    print("Signals saved to database.")

# Main
if __name__ == "__main__":
    df = load_stock_data()
    df = generate_signals(df)
    save_signals_to_db(df)
