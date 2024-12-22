from flask import Flask, jsonify
from datetime import datetime
from fetch_stocks import fetch_stocks, fetch_current_prices
from db_operations import db, init_db, add_stocks, Stock
from flask_apscheduler import APScheduler
import logging

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
        all_stocks = Stock.query.all()  # Query all stock records
        stocks_to_check = [{'name': stock.name, 'symbol': stock.symbol, 'tracked_opening_price': stock.tracked_opening_price} for stock in all_stocks]
        
        # Fetch current prices
        current_prices = fetch_current_prices(stocks_to_check)

        # Find matching stocks (within 2% range)
        matching_stocks = [
            {
                'name': stock['name'],
                'symbol': stock['symbol'],
                'tracked_opening_price': stock['tracked_opening_price'],
                'current_price': current_prices.get(stock['symbol'])
            }
            for stock in stocks_to_check
            if current_prices.get(stock['symbol']) is not None and \
               (current_prices[stock['symbol']] >= stock['tracked_opening_price'] * 0.98 and \
                current_prices[stock['symbol']] <= stock['tracked_opening_price'] * 1.02)
        ]

        return jsonify(matching_stocks)
    except Exception as e:
        logging.error(f"Error in get_matching_stocks: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Define a job to call the get_stocks function every 5 minutes
@scheduler.task('interval', id='fetch_stocks_job', seconds=300)  # 300 seconds = 5 minutes
def fetch_stocks_job():
    with app.app_context():  # Ensure the app context is available
        try:
            logging.info("Fetching stocks...")
            get_stocks()  # Call the get_stocks function
        except Exception as e:
            logging.error(f"Error fetching stocks: {str(e)}")

if __name__ == '__main__':
    scheduler.init_app(app)  # Initialize the scheduler with the app
    scheduler.start()         # Start the scheduler
    app.run(debug=True, host='0.0.0.0')
