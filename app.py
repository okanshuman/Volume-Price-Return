from flask import Flask, jsonify
from datetime import datetime
from fetch_stocks import fetch_stocks, fetch_current_prices
from db_operations import db, init_db, add_stocks, Stock, remove_old_stocks
from flask_apscheduler import APScheduler
import logging
import requests

# Set up basic logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Configure the database connection
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://casaos:casaos@localhost/stocks_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
init_db(app)

# Set up the APScheduler
scheduler = APScheduler()

# Global variable to store matching stocks and notified stocks
latest_matching_stocks = []
notified_stocks = set()  # Set to track notified stock symbols

# Telegram Bot Token and Chat ID
TELEGRAM_TOKEN = '7864062800:AAHGK0DdXYiTsgnmM7rcIzXe6VkZ0v60vZU'  # Your bot token
CHAT_ID = '390415235'  # Your chat ID

# Function to send notification to Telegram
def send_telegram_notification(stock):
    message = f"New matching stock added:\nName: {stock['name']}\nSymbol: {stock['symbol']}\nTracked Opening Price: {stock['tracked_opening_price']}\nCurrent Price: {stock['current_price']}"

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'  # Optional: Use Markdown formatting
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logging.info("Notification sent successfully.")
        else:
            logging.error(f"Failed to send notification: {response.text}")
    except Exception as e:
        logging.error(f"Error sending notification: {str(e)}")

@app.route('/')
def home():
    return app.send_static_file('index.html')

@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    try:
        current_date = datetime.now().strftime("%Y-%m-%d")
        stocks = fetch_stocks()
        
        # Store fetched stocks in the database
        add_stocks(stocks, current_date)
        
        return jsonify({
            'date': current_date,
            'stocks': stocks
        })
    except Exception as e:
        logging.error(f"Error in get_stocks: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/all_stocks', methods=['GET'])
def get_all_stocks():
    try:
        all_stocks = Stock.query.all()  # Query all stock records
        result = [{'name': stock.name, 'symbol': stock.symbol, 'date': stock.date, 'tracked_opening_price': stock.tracked_opening_price} for stock in all_stocks]
        
        logging.info(f"Fetched stocks: {result}")  # Log the fetched stocks
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error in get_all_stocks: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/matching_stocks', methods=['GET'])
def get_matching_stocks():
    try:
        return jsonify(latest_matching_stocks)  # Return the latest matching stocks
    except Exception as e:
        logging.error(f"Error in get_matching_stocks: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Define a job to remove old stocks every day (24 hours)
@scheduler.task('interval', id='remove_old_stocks_job', hours=24)  
def remove_old_stocks_job():
    with app.app_context():  # Ensure the app context is available
        try:
            logging.info("Removing old stocks...")
            remove_old_stocks()  # Call the function to remove old stocks
        except Exception as e:
            logging.error(f"Error removing old stocks: {str(e)}")

# Define a job to fetch new stocks every 5 minutes
@scheduler.task('interval', id='fetch_new_stocks_job', minutes=15)
def fetch_new_stocks_job():
    with app.app_context():  # Ensure the app context is available
        try:
            logging.info("Fetching new stocks from /api/stocks...")
            response = requests.get('http://localhost:5000/api/stocks')  # Adjust URL if needed for deployment
            if response.status_code == 200:
                data = response.json()
                logging.info(f"Fetched new stocks: {data}")
            else:
                logging.error(f"Failed to fetch new stocks: {response.status_code} - {response.text}")
        except Exception as e:
            logging.error(f"Error fetching new stocks: {str(e)}")

# Define a job to fetch matching stocks every minute
@scheduler.task('interval', id='fetch_matching_stocks_job', minutes=3)
def fetch_matching_stocks_job():
    global latest_matching_stocks  # Use global variable to store matching stocks
    with app.app_context():  # Ensure the app context is available
        try:
            logging.info("Fetching matching stocks...")
            all_stocks = Stock.query.all()  # Get all stocks from the database
            stocks_to_check = [{'name': stock.name, 'symbol': stock.symbol, 'tracked_opening_price': stock.tracked_opening_price} for stock in all_stocks]
            current_prices = fetch_current_prices(stocks_to_check)  # Fetch current prices
            
            # Logic to find matching stocks (within ±2%)
            matching_stocks = {}
            for stock in stocks_to_check:
                current_price = current_prices.get(stock['symbol'])
                if current_price is not None and \
                   (current_price >= stock['tracked_opening_price'] * 0.98 and \
                    current_price <= stock['tracked_opening_price'] * 1.02):
                    if stock['symbol'] not in matching_stocks:
                        matching_stocks[stock['symbol']] = {
                            'name': stock['name'],
                            'symbol': stock['symbol'],
                            'tracked_opening_price': stock['tracked_opening_price'],
                            'current_price': current_price
                        }
                        # Check if we have already notified about this stock
                        if stock['symbol'] not in notified_stocks:
                            send_telegram_notification(matching_stocks[stock['symbol']])
                            notified_stocks.add(stock['symbol'])  # Mark this stock as notified
            
            latest_matching_stocks = list(matching_stocks.values())  # Store unique entries only
            logging.info(f"Updated matching stocks: {latest_matching_stocks}")

        except Exception as e:
            logging.error(f"Error fetching matching stocks: {str(e)}")

if __name__ == '__main__':
    scheduler.init_app(app)  # Initialize the scheduler with the app
    scheduler.start()         # Start the scheduler
    app.run(debug=True, host='0.0.0.0')
