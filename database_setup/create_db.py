import sqlite3

# Create a connection to the SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('naijastock.db')

# Create a cursor object to interact with the database
cursor = conn.cursor()

# Create table to store stock data (date, ticker, open, high, low, close, volume)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS stock_data (
        date TEXT,
        ticker TEXT,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume INTEGER
    )
''')

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Database and table 'stock_data' created successfully.")
