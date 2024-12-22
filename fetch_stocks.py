# fetch_stocks.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
import yfinance as yf  # Import yfinance
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Set up basic logging configuration
logging.basicConfig(level=logging.INFO)

def fetch_current_prices(stocks):
    current_prices = {}
    for stock in stocks:
        ticker_symbol = stock['symbol']
        try:
            ticker = yf.Ticker(ticker_symbol)
            current_data = ticker.history(period="1d")
            if not current_data.empty:
                current_prices[ticker_symbol] = current_data['Close'].iloc[-1]  # Get the latest closing price
        except Exception as e:
            logging.error(f"Error fetching current price for {ticker_symbol}: {e}")
    return current_prices

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
    chrome_options.add_argument("--headless")  # Run headless Chrome
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=ChromeService(executable_path='/usr/bin/chromedriver'), options=chrome_options)
    
    logging.info(f"Fetching stocks from {url}")
    driver.get(url)
    
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'table-striped')))
    
    stocks = []
    try:
        stock_list = driver.find_element("class name", 'table-striped')
        rows = stock_list.find_elements("tag name", 'tr')[1:]  # Skip the header row

        logging.info(f"Found {len(rows)} rows of stock data.")
        
        for row in rows:
            columns = row.find_elements("tag name", 'td')
            if len(columns) > 1:
                stock_name = columns[1].text.strip()
                stock_symbol = columns[2].text.strip().replace('$', '') + '.NS'  # Remove $ and append .NS for NSE
                
                opening_price = fetch_opening_price(stock_symbol)

                if opening_price is not None:
                    stocks.append({'name': stock_name, 'symbol': stock_symbol, 'opening_price': opening_price}) 
                    logging.info(f"Added stock: {stock_name} ({stock_symbol}) with opening price: {opening_price}")

    except Exception as e:
        logging.error(f"An error occurred while fetching stocks: {e}")

    driver.quit()
    
    logging.info(f"Fetched stocks: {stocks}")
    return stocks

if __name__ == "__main__":
    fetched_stocks = fetch_stocks()
    print(fetched_stocks)
