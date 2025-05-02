import sqlite3
import pandas as pd

conn = sqlite3.connect('naijastock.db')
df = pd.read_sql("SELECT * FROM stock_data", conn)
conn.close()

print(df[['date', 'ticker']].head(10))
print("\nData types:\n", df.dtypes)
