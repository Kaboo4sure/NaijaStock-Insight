import sqlite3
import pandas as pd

# Connect to your local SQLite database
conn = sqlite3.connect("naijastock.db")

# Extract all distinct tickers from stock_data table
df = pd.read_sql("SELECT DISTINCT ticker FROM stock_data", conn)

# Close the connection
conn.close()

# Add an empty column for company name
df['company_name'] = ""

# Save to CSV
df = df.sort_values(by="ticker").reset_index(drop=True)
df.to_csv("company_lookup_template.csv", index=False)

print("✅ company_lookup_template.csv generated successfully.")
