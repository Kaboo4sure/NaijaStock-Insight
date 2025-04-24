import sqlite3
import pandas as pd

# Function to connect to SQLite database and retrieve stock data
def fetch_stock_data():
    conn = sqlite3.connect('naijastock.db')
    query = """
    SELECT date, ticker, open, high, low, close, volume
      FROM stock_data
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Function to display the first 5 rows
def display_top_5(df):
    if df.empty:
        print("No data available to display.")
    else:
        print(df.head())

# Function to display basic statistics about the stock data
def display_statistics(df):
    print("\nStatistics for stock data:")
    print(f"Total records: {len(df)}")
    print(f"Average Open Price: {df['open'].mean():.2f}")
    print(f"Average Close Price: {df['close'].mean():.2f}")
    print(f"Average Volume: {df['volume'].mean():.0f}")
    print(f"Max Close Price: {df['close'].max():.2f}")
    print(f"Min Close Price: {df['close'].min():.2f}")

def main():
    df = fetch_stock_data()
    
    print("\nTop 5 Stock Data:")
    display_top_5(df)
    
    display_statistics(df)

if __name__ == "__main__":
    main()
