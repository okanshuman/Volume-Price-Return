from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
import yfinance as yf  # Import yfinance
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def fetch_stocks():
    url = "https://chartink.com/screener/copy-volume-shockers-12446"

    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=ChromeService(executable_path='/usr/bin/chromedriver'), options=chrome_options)

    driver.get(url)
    
    # Use WebDriverWait instead of sleep for better reliability
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'table-striped')))

    stocks = []
    try:
        stock_list = driver.find_element("class name", 'table-striped')
        rows = stock_list.find_elements("tag name", 'tr')[1:]

        for row in rows:
            columns = row.find_elements("tag name", 'td')
            if len(columns) > 1:
                stock_name = columns[1].text.strip()
                stock_symbol = columns[2].text.strip().replace('$', '') + '.NS'  # Remove $ and append .NS for NSE

                # Fetch opening price using yfinance
                ticker = yf.Ticker(stock_symbol)  # Create a Ticker object
                try:
                    historical_data = ticker.history(period="1d")  # Fetch historical data for 1 day
                    opening_price = historical_data['Open'].iloc[0] if not historical_data.empty else None
                    
                    # Convert opening price to integer if it's not None
                    opening_price = int(opening_price) if opening_price is not None else None

                except Exception as e:
                    logging.error(f"Error fetching opening price for {stock_symbol}: {e}")
                    opening_price = None

                stocks.append({'name': stock_name, 'symbol': stock_symbol, 'opening_price': opening_price})

    except Exception as e:
        logging.error(f"An error occurred: {e}")

    driver.quit()
    
    return stocks
