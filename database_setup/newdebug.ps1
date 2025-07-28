import sqlite3
import pandas as pd

conn = sqlite3.connect("naijastock.db")
df = pd.read_sql("SELECT ticker, COUNT(*) as count, MAX(date) as latest_date FROM stock_data GROUP BY ticker ORDER BY latest_date DESC", conn)
print(df.head(20))
conn.close()
