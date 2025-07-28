import pandas as pd
import sqlite3

def generate_signals(df):
    df.columns = df.columns.str.lower()
    required_cols = ['date', 'close', 'ticker']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])

    all_signals = []

    for ticker, group in df.groupby('ticker'):
        group = group.sort_values('date').copy()

        if len(group) < 2:
            print(f"Skipping {ticker} (only {len(group)} row)")
            continue

        # ✅ Simple signal: 1 if price went up from previous day
        group['price_change'] = group['close'].pct_change()
        group['signal_score'] = (group['price_change'] > 0).astype(int)

        # Resample weekly, get last available row each week
        weekly = group.set_index('date').resample('W-FRI').last().dropna(subset=['close']).copy()
        weekly['ticker'] = ticker
        all_signals.append(weekly[['ticker', 'signal_score']].reset_index())

    if all_signals:
        final_df = pd.concat(all_signals).sort_values(by=['ticker', 'date']).reset_index(drop=True)
        final_df.to_csv("fallback_signals_output.csv", index=False)
        print(final_df.tail(10))
        return final_df
    else:
        print("⚠️ No valid data found for any ticker.")
        return pd.DataFrame(columns=['date', 'ticker', 'signal_score'])

# Main block
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
