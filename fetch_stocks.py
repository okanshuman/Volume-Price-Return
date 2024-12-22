from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
import yfinance as yf  # Import yfinance
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def fetch_opening_price(ticker_symbol):
    attempts = 3
    for attempt in range(attempts):
        try:
            ticker = yf.Ticker(ticker_symbol)
            historical_data = ticker.history(period="1d")
            return int(historical_data['Open'].iloc[0]) if not historical_data.empty else None
        except Exception as e:
            logging.error(f"Attempt {attempt + 1}: Error fetching opening price for {ticker_symbol}: {e}")
            time.sleep(2)  # Wait before retrying
    return None  # Return None if all attempts fail

def fetch_stocks():
    url = "https://chartink.com/screener/copy-volume-shockers-12446"
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=ChromeService(executable_path='/usr/bin/chromedriver'), options=chrome_options)
    
    driver.get(url)
    
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
                
                opening_price = fetch_opening_price(stock_symbol)

                if opening_price is not None:
                    stocks.append({'name': stock_name, 'symbol': stock_symbol, 'opening_price': opening_price}) 

    except Exception as e:
        logging.error(f"An error occurred: {e}")

    driver.quit()
    
    return stocks
