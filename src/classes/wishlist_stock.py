import yfinance as yf
from datetime import datetime

class Wishlist_Stock:
    def __init__(self, ticker_code, suffix, wishlist_data=None, requires_fetching=True):
        self.ticker_code = ticker_code
        self.suffix = suffix
        self.yfticker = yf.Ticker(f"{self.ticker_code}.{self.suffix}")
        self.buy_threshold = None
        self.sell_threshold = None
        self.status = ""
        self.delete = False
        self.last_fetched_price = None

        if requires_fetching:
            self.last_fetched_price = self.get_today_data()
        elif wishlist_data:
            self.load_existing_data(wishlist_data)

    def load_existing_data(self, wishlist_data):
        self.buy_threshold = wishlist_data.get('BUY')
        self.sell_threshold = wishlist_data.get('SELL')
        self.status = wishlist_data.get('STATUS', "")
        self.delete = wishlist_data.get('Delete', False)
        self.last_fetched_price = wishlist_data.get('Current Price')

    def to_dict(self):
        return {
            "Current Price": self.last_fetched_price,
            "exchange": self.suffix,
            "BUY": self.buy_threshold,
            "SELL": self.sell_threshold,
            "STATUS": self.status,
            "Delete": self.delete
        }
    
    def get_today_data(self):
        data = self.yfticker.history(period='1d')
        if data.empty:
            raise ValueError(f"{self.ticker_code}.{self.suffix}: possibly delisted or invalid ticker.")
        return data['Close'].values[0]

