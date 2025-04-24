from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options  # Import Options
from webdriver_manager.chrome import ChromeDriverManager
import sqlite3
import pandas as pd
import time

# Step 1: Initialize the Chrome WebDriver with WebDriverManager (Headless mode)
chrome_options = Options()
chrome_options.add_argument("--headless")  # This will run the browser in headless mode
chrome_options.add_argument("--disable-gpu")  # Disable GPU usage for headless mode
chrome_options.add_argument("--no-sandbox")  # Required for some systems to work with headless mode

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)  # Pass options to WebDriver

# Step 2: Navigate to the NGX equities price list page
url = 'https://ngxgroup.com/exchange/data/equities-price-list/'
driver.get(url)

# Step 3: Allow time for the page to load fully
time.sleep(10)  # Adjust the sleep time if needed for the page to load

all_rows = []  # List to store data from all pages
page_number = 1  # Start with the first page

# Function to check if the "Next" button is disabled
def is_next_button_disabled():
    try:
        next_button = driver.find_element(By.LINK_TEXT, 'Next')
        if 'disabled' in next_button.get_attribute('class'):
            return True
        return False
    except Exception as e:
        print(f"Could not check if 'Next' button is disabled: {e}")
        return True

# Function to click "Next" button if enabled
def go_to_next_page():
    try:
        next_button = driver.find_element(By.LINK_TEXT, 'Next')
        driver.execute_script("arguments[0].scrollIntoView();", next_button)
        driver.execute_script("arguments[0].click();", next_button)
        time.sleep(5)  # Wait for the page to load
        return True
    except Exception as e:
        print(f"Could not navigate to next page: {e}")
        return False

while True:
    print(f"Processing page {page_number}")

    # Step 3: Locate the table on the page
    try:
        table = driver.find_element(By.TAG_NAME, 'table')
    except Exception as e:
        print(f"Table not found on page {page_number}: {e}")
        break

    # Step 4: Extract table headers (do this only once, as headers are the same across pages)
    if page_number == 1:
        headers = [th.text.strip() for th in table.find_elements(By.TAG_NAME, 'th')]

    # Step 5: Extract table rows
    rows = []
    for tr in table.find_elements(By.TAG_NAME, 'tr')[1:]:  # Skip header row
        cells = tr.find_elements(By.TAG_NAME, 'td')
        row = [cell.text.strip() for cell in cells]
        rows.append(row)
    all_rows.extend(rows)  # Add rows from current page to all_rows

    # Step 6: Check if the "Next" button is disabled
    if is_next_button_disabled():
        print("Reached the last page or 'Next' button is disabled.")
        break  # Exit the loop if the "Next" button is disabled

    # Step 7: Go to next page if "Next" button is enabled
    if not go_to_next_page():
        break  # Exit the loop if navigation fails

    page_number += 1

# Step 8: Convert the data to a DataFrame
df = pd.DataFrame(all_rows, columns=headers)

# Step 9: Store data in SQLite database
def store_data_in_db():
    # Connect to SQLite database
    conn = sqlite3.connect('naijastock.db')
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS stock_data (
                        date TEXT,
                        ticker TEXT,
                        open REAL,
                        high REAL,
                        low REAL,
                        close REAL,
                        volume INTEGER
                    )''')

    # Insert data into the database
    for row in all_rows:
        date_str = row[0]  # Assuming the date is in the first column
        ticker = row[1]  # Assuming the ticker is in the second column
        
        # Handle price fields, replace '--' with 0
        try:
            open_price = float(row[2]) if row[2] != '--' else 0
            high_price = float(row[3]) if row[3] != '--' else 0
            low_price = float(row[4]) if row[4] != '--' else 0
            close_price = float(row[5]) if row[5] != '--' else 0
        except ValueError:
            open_price = high_price = low_price = close_price = 0

        # Handle the volume field more carefully
        try:
            volume = int(row[6]) if row[6] and row[6].replace('.', '', 1).isdigit() else 0
        except ValueError:
            volume = 0  # Set volume to 0 if conversion fails

        # Insert each row into the stock_data table
        cursor.execute('''INSERT INTO stock_data (date, ticker, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                        (date_str, ticker, open_price, high_price, low_price, close_price, volume))

    # Commit changes and close the connection
    conn.commit()
    conn.close()
    print("Data successfully stored in the database.")

# Call the function to store data
store_data_in_db()

# Step 10: Close the WebDriver
driver.quit()
