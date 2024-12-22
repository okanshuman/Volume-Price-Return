from flask_sqlalchemy import SQLAlchemy
import logging

db = SQLAlchemy()

class Stock(db.Model):
    __tablename__ = 'stock'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    tracked_opening_price = db.Column(db.Float, nullable=True)

    # Unique constraint on symbol, date, and tracked_opening_price
    __table_args__ = (
        db.UniqueConstraint('symbol', 'date', 'tracked_opening_price', name='unique_stock_constraint'),
    )

def init_db(app):
    with app.app_context():
        db.init_app(app)
        db.create_all()

def add_stocks(stocks, current_date):
    try:
        for stock in stocks:
            # Check if an entry already exists with the same symbol, date, and tracked_opening_price
            existing_stock = Stock.query.filter_by(
                symbol=stock['symbol'],
                date=current_date,
                tracked_opening_price=stock['opening_price']
            ).first()

            if existing_stock is None:
                new_stock = Stock(
                    name=stock['name'],
                    symbol=stock['symbol'],
                    date=current_date,
                    tracked_opening_price=stock['opening_price']
                )
                db.session.add(new_stock)

        db.session.commit()  # Commit all new stocks to the database
    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        logging.error(f"Error adding stocks: {str(e)}")
        raise  # Re-raise the exception after logging
