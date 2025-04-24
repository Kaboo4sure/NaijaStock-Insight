import yfinance as yf
import sqlite3
import pandas as pd

# List of stock tickers to download data for
stocks = ['NSTL.NE']

def fetch_and_store_data():
    # Connect to the SQLite database
    conn = sqlite3.connect('naijastock.db')
    cursor = conn.cursor()

    for stock in stocks:
        try:
            # Fetch historical data from Yahoo Finance
            data = yf.download(stock, start='2022-01-01')

            # Check if the data is empty
            if data.empty:
                print(f"No data found for {stock}. Skipping.")
                continue

            # Insert each row of data into the database
            for index, row in data.iterrows():
                # Convert the index (Timestamp) to a string in 'YYYY-MM-DD' format
                date_str = index.strftime('%Y-%m-%d')

                # Access row values directly to avoid 'Series' object error
                open_price = row['Open'].iloc[0] if isinstance(row['Open'], pd.Series) else row['Open']
                high_price = row['High'].iloc[0] if isinstance(row['High'], pd.Series) else row['High']
                low_price = row['Low'].iloc[0] if isinstance(row['Low'], pd.Series) else row['Low']
                close_price = row['Close'].iloc[0] if isinstance(row['Close'], pd.Series) else row['Close']
                volume = row['Volume'].iloc[0] if isinstance(row['Volume'], pd.Series) else row['Volume']

                # Insert into the database
                cursor.execute('''
                    INSERT INTO stock_data (date, ticker, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (date_str, stock, float(open_price), float(high_price), float(low_price), float(close_price), int(volume)))

            print(f"Data for {stock} inserted into database successfully.")
        except Exception as e:
            print(f"Failed to download data for {stock}: {str(e)}")

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

# Call the function to fetch and store data
fetch_and_store_data()
