import sqlite3

# Print the message to confirm which database is being used
print("Using database file: naijastock.db")

# Connect to SQLite database
conn = sqlite3.connect('naijastock.db')
cursor = conn.cursor()

# Check if the stock_data table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables in the database:", tables)

# Close the connection
conn.close()
