import pandas_ta as ta
import pandas as pd

def generate_signals(df):
    # ✅ 1. Standardize column names (optional but safer)
    df.columns = df.columns.str.lower()

    # ✅ 2. Ensure required columns exist
    required_cols = ['date', 'close', 'volume']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # ✅ 3. Convert 'date' to datetime
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])

    # ✅ 4. Technical indicators
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

    # ✅ 5. Signal generation rule
    df['signal_score'] = 0
    df.loc[
        (df['five_day_return'] > 0) &
        (df['RSI'] < 70) &
        (df['macd'] > df['macdsignal']) &
        (df['volume_spike'] == True),
        'signal_score'
    ] = 1  # BUY signal

    # ✅ 6. Final cleanup (optional: reset index if needed)
    df.reset_index(drop=True, inplace=True)

    # ✅ 7. Print tail for verification
    if 'ticker' in df.columns:
        print(df[['date', 'ticker', 'signal_score']].tail())
    else:
        print(df[['date', 'signal_score']].tail())

    return df
