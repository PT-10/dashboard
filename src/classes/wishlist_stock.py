import yfinance as yf
from datetime import datetime

class Wishlist_Stock():
    def __init__(self, ticker_code, suffix):
        self.ticker_code = ticker_code
        self.suffix = suffix
        self.yfticker = yf.Ticker(f"{self.ticker_code}.{self.suffix}")
        self.buy_threshold = None
        self.sell_threshold = None
        # self.today = pd.to_datetime('today').date()
        self.last_fetched_price = self.get_today_data()
        self.last_fetched_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # self.buy_price = self.get_buy_price()
        # self.sell_price = self.get_sell_price()

    def get_today_data(self):
        if self.yfticker.history(period='1d').empty:
            return None
        today_data = self.yfticker.history(period='1d')
        return today_data['Close'].values[0] if not today_data.empty else None

