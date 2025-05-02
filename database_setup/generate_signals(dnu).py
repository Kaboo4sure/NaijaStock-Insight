import sqlite3
import pandas as pd
import talib

# Function to load stock data from the database
def load_stock_data():
    # Change to the correct database file
    conn = sqlite3.connect('naijastock.db')  # Correct database file
    df = pd.read_sql("SELECT * FROM stock_data", conn, parse_dates=["date"])  # Simply use parse_dates
    conn.close()

    # Drop rows where the 'date' column has invalid values (NaT)
    df = df.dropna(subset=['date'])
    return df

# Function to generate signals
def generate_signals(df):
    # Calculate 5-day return (Momentum)
    df['five_day_return'] = df['close'].pct_change(5) * 100

    # Calculate RSI (Relative Strength Index)
    df['RSI'] = talib.RSI(df['close'], timeperiod=14)

    # Calculate MACD (Moving Average Convergence Divergence)
    df['macd'], df['macdsignal'], df['macdhist'] = talib.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)

    # Calculate Volume Spike (compare today's volume with the 20-day average)
    df['twenty_day_avg_volume'] = df['volume'].rolling(window=20).mean()
    df['volume_spike'] = df['volume'] > df['twenty_day_avg_volume']

    # Generate Signal Score
    df['signal_score'] = 0
    df.loc[
        (df['five_day_return'] > 0) &
        (df['RSI'] < 70) &
        (df['macd'] > df['macdsignal']) &
        (df['volume_spike'] == True),
        'signal_score'
    ] = 1  # 1 indicates a BUY signal

    return df

# Function to save the generated signals to the database
def save_signals_to_db(df):
    # Change to the correct database file
    conn = sqlite3.connect('naijastock.db')  # Correct database file
    cursor = conn.cursor()

    # Create a new table for weekly signals if not exists
    cursor.execute('''CREATE TABLE IF NOT EXISTS weekly_signals (
                        date TEXT,
                        ticker TEXT,
                        five_day_return REAL,
                        RSI REAL,
                        macd REAL,
                        macdsignal REAL,
                        volume_spike BOOLEAN,
                        signal_score INTEGER
                    )''')

    # Insert the generated signals into the database
    for _, row in df.iterrows():
        cursor.execute('''INSERT INTO weekly_signals (date, ticker, five_day_return, RSI, macd, macdsignal, volume_spike, signal_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                        (row['date'], row['ticker'], row['five_day_return'], row['RSI'], row['macd'], row['macdsignal'], row['volume_spike'], row['signal_score']))

    conn.commit()
    conn.close()
    print("Signals successfully saved to the database.")

# Main execution
if __name__ == "__main__":
    # Load stock data
    df = load_stock_data()

    # Generate signals
    df = generate_signals(df)

    # Save the signals to the database
    save_signals_to_db(df)
