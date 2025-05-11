import sqlite3
import pandas as pd

# Load lookup table
lookup = pd.read_csv("company_lookup.csv")
lookup.columns = lookup.columns.str.lower()

# Connect to DB
conn = sqlite3.connect("naijastock.db")
cursor = conn.cursor()

# Step 1: Add company_name column if it doesn't exist
cursor.execute("PRAGMA table_info(stock_data);")
columns = [col[1] for col in cursor.fetchall()]
if 'company_name' not in columns:
    cursor.execute("ALTER TABLE stock_data ADD COLUMN company_name TEXT;")
    print("✅ Added 'company_name' column to stock_data")

# Step 2: Load all records with ticker
df = pd.read_sql("SELECT rowid, * FROM stock_data", conn)

# Step 3: Merge with lookup
df = df.merge(lookup, how="left", on="ticker")

# Step 4: Update the database with company names
for _, row in df.iterrows():
    if pd.notna(row['company_name_y']):
        cursor.execute(
            "UPDATE stock_data SET company_name = ? WHERE rowid = ?",
            (row['company_name_y'], row['rowid'])
        )

conn.commit()
conn.close()
print("✅ company_name values updated successfully.")
