import sqlite3
import os

# Path to the SQLite database
DB_PATH = 'naijastock.db'

# Function to clear all data from the stock_data table
def clear_database():
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Delete all records from the stock_data table
        cursor.execute("DELETE FROM stock_data")
        conn.commit()  # Commit the changes to the database
        print("Database cleared successfully.")

        # Close the connection
        conn.close()

    except Exception as e:
        print(f"Error clearing database: {e}")

if __name__ == "__main__":
    # Run the clear_database function when this script is executed
    clear_database()
