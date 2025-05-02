import pandas_ta as ta

def generate_signals(df):
    # Calculate 5-day return (Momentum)
    df['five_day_return'] = df['close'].pct_change(5) * 100

    # Calculate RSI (Relative Strength Index)
    df['RSI'] = ta.rsi(df['close'], length=14)

    # Calculate MACD (Moving Average Convergence Divergence)
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    if macd is not None:
        df['macd'] = macd['MACD_12_26_9']
        df['macdsignal'] = macd['MACDs_12_26_9']
        df['macdhist'] = macd['MACDh_12_26_9']
    else:
        df['macd'] = df['macdsignal'] = df['macdhist'] = float('nan')

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
