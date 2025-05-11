from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import sqlite3
import pandas as pd
import time

# Step 1: Initialize Chrome WebDriver in headless mode
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

# Step 2: Navigate to NGX equities price list page
url = 'https://ngxgroup.com/exchange/data/equities-price-list/'
driver.get(url)

# Step 3: Allow page to fully load
time.sleep(10)

all_rows = []
page_number = 1

# Check if the "Next" button is disabled
def is_next_button_disabled():
    try:
        next_button = driver.find_element(By.LINK_TEXT, 'Next')
        return 'disabled' in next_button.get_attribute('class')
    except Exception as e:
        print(f"Could not check 'Next' button: {e}")
        return True

# Click "Next" button if available
def go_to_next_page():
    try:
        next_button = driver.find_element(By.LINK_TEXT, 'Next')
        driver.execute_script("arguments[0].scrollIntoView();", next_button)
        driver.execute_script("arguments[0].click();", next_button)
        time.sleep(5)
        return True
    except Exception as e:
        print(f"Could not go to next page: {e}")
        return False

# Loop through all pages
while True:
    print(f"Processing page {page_number}")
    try:
        table = driver.find_element(By.TAG_NAME, 'table')
    except Exception as e:
        print(f"Table not found: {e}")
        break

    # Only extract headers on the first page
    if page_number == 1:
        headers = [th.text.strip() for th in table.find_elements(By.TAG_NAME, 'th')]

    # Extract rows from table
    for tr in table.find_elements(By.TAG_NAME, 'tr')[1:]:
        cells = tr.find_elements(By.TAG_NAME, 'td')
        if len(cells) >= 11:
            try:
                company_name = cells[0].text.strip()
                open_price = float(cells[2].text.strip().replace(',', '') or 0)
                high_price = float(cells[3].text.strip().replace(',', '') or 0)
                low_price = float(cells[4].text.strip().replace(',', '') or 0)
                close_price = float(cells[5].text.strip().replace(',', '') or 0)
                volume_text = cells[8].text.strip().replace(',', '')
                volume = int(volume_text) if volume_text and volume_text.isdigit() else 0
                trade_date = cells[10].text.strip()
                ticker = company_name.split()[0]  # Fallback if no separate ticker column

                all_rows.append([
                    trade_date, ticker, company_name, open_price, high_price, low_price, close_price, volume
                ])
            except Exception as e:
                print(f"❌ Failed to parse row: {e}")

    if is_next_button_disabled():
        print("Reached last page.")
        break

    if not go_to_next_page():
        break

    page_number += 1

# Step 8: Store data in SQLite database
def store_data_in_db():
    conn = sqlite3.connect('naijastock.db')
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS stock_data (
                        date TEXT,
                        ticker TEXT,
                        company_name TEXT,
                        open REAL,
                        high REAL,
                        low REAL,
                        close REAL,
                        volume INTEGER
                    )''')

    for row in all_rows:
        cursor.execute('''INSERT INTO stock_data 
                          (date, ticker, company_name, open, high, low, close, volume)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', row)

    conn.commit()
    conn.close()
    print("✅ Data stored successfully in naijastock.db")

store_data_in_db()
driver.quit()
