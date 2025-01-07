import os
import pandas as pd
import yfinance as yf
from datetime import datetime
from utils.historic_data import download_historic_info

   

class Stock:
    def __init__(self, ticker_code, purchase_date, dashboard, threshold_percentage, requires_fetching=True):
        self.ticker_code = ticker_code
        self.suffix = None
        self.yfticker = None
        self.purchase_date = purchase_date
        self.threshold_percentage = threshold_percentage
        self.dashboard = dashboard
        self.today = pd.to_datetime('today').date()
        self.historical_data = pd.DataFrame()
        self.today_data = None
        self.avg_price = None
        self.max_price = None
        self.num_shares = None
        self.threshold_price = None
        self.investment_val = None
        self.present_val = None
        self.last_fetched_price = None
        self.last_fetched_time = None
        self.buy_threshold = None
        self.sell_threshold = None
        self.status = None
        self.historic_file_path = None
        if requires_fetching:
            # print(self.ticker_code, self.suffix)
            # logging.info(f"Initializing {self.ticker_code} for fetching.")
            self.update_data()
            # self.add_to_dashboard_json()
        else:
            self.load_existing_data()

    def update_data(self):
        self.suffix = self.get_suffix() if self.suffix is None else self.suffix
        self.yfticker = yf.Ticker(f"{self.ticker_code}.{self.suffix}")
        self.historical_data = self.fetch_historical_data()
        self.max_price = self.get_max_price()
        self.avg_price = self.get_avg_price()
        self.threshold_price = self.get_threshold_price()
        self.num_shares = self.get_num_shares()
        self.investment_val = self.get_investment()
        self.present_val = self.get_present_value()
        self.last_fetched_price = self.get_today_data()
        self.last_fetched_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.historic_file_path = f"data/stock_historic_data/{self.ticker_code}_{self.suffix}.json"

    def load_existing_data(self):
        if self.ticker_code in self.dashboard.purchase_info:
            info = self.dashboard.purchase_info[self.ticker_code]
            self.suffix = info['suffix']
            self.yfticker = yf.Ticker(f"{self.ticker_code}.{self.suffix}")
            self.max_price = info['max_price']
            self.avg_price = info['average_price']
            self.historical_data = pd.DataFrame(info['historic_data'])
            self.historical_data['Date'] = pd.to_datetime(self.historical_data['Date'])
            self.historical_data.set_index('Date', inplace=True)
            self.threshold_price = info['threshold_price']
            self.num_shares = self.get_num_shares()
            self.investment_val = self.get_investment()
            self.last_fetched_price = info['last_fetched_price']
            self.last_fetched_time = info['last_fetched_time']
            self.present_val = self.num_shares * self.last_fetched_price
            self.buy_threshold = info['BUY']
            self.sell_threshold = info['SELL']
            self.status = info['STATUS']
            self.historic_file_path = f"data/stock_historic_data/{self.ticker_code}_{self.suffix}.json"


    def get_suffix(self):
        ticker = f"{self.ticker_code}.NS"
        ticker_obj = yf.Ticker(ticker)
        if ticker_obj.history(period='1d').empty:
            ticker = f"{self.ticker_code}.BO"
            ticker_obj = yf.Ticker(ticker)
        if ticker_obj.history(period='1d').empty:
            return None
        return "NS" if ticker == f"{self.ticker_code}.NS" else "BO"

    def fetch_historical_data(self):
        if self.yfticker.history(period='1d').empty:
            return pd.DataFrame()
        purchase_date = pd.to_datetime(self.purchase_date).date()
        if (self.today - purchase_date).days < 5:
            start_date = self.today - pd.Timedelta(days=15)
            historical_data = self.yfticker.history(start=start_date)
        else:
            historical_data = self.yfticker.history(start=purchase_date)
        return historical_data

    def get_today_data(self):
        if self.yfticker.history(period='1d').empty:
            return None
        today_data = self.yfticker.history(period='1d')
        return today_data['Close'].values[0] if not today_data.empty else None

    def get_max_price(self):
        if self.yfticker.history(period='1d').empty:
            return None
        purchase_date = pd.to_datetime(self.purchase_date).date()
        historical_data = self.historical_data[self.historical_data.index.date >= purchase_date]
        return historical_data['High'].max().round(2) if not historical_data.empty else None
    
    def get_threshold_price(self):
        threshold_price = self.max_price * (1 - self.threshold_percentage * 0.01)
        return round(threshold_price, 2)

    def get_avg_price(self):
        #get information from purchase_json
        if self.ticker_code in self.dashboard.purchase_info:
        
            if self.dashboard.new_csv:
                row = self.dashboard.get_holdings_data().loc[self.dashboard.get_holdings_data()['Instrument'] == self.ticker_code]
                return row['Avg. cost'].values[0] if not row.empty else None
            
            else:
                return self.dashboard.purchase_info[self.ticker_code]['average_price']
        else:
            row = self.dashboard.get_holdings_data().loc[self.dashboard.get_holdings_data()['Instrument'] == self.ticker_code]
            return row['Avg. cost'].values[0] if not row.empty else None
            

    def get_num_shares(self):
        if self.ticker_code in self.dashboard.purchase_info:
            if self.dashboard.new_csv:
                row = self.dashboard.get_holdings_data().loc[self.dashboard.get_holdings_data()['Instrument'] == self.ticker_code]
                return int(row['Qty.'].values[0]) if not row.empty else None
            else:
                return self.dashboard.purchase_info[self.ticker_code]['num_shares']    

        else:
            row = self.dashboard.get_holdings_data().loc[self.dashboard.get_holdings_data()['Instrument'] == self.ticker_code]
            return int(row['Qty.'].values[0]) if not row.empty else None

    def get_investment(self):
        if self.ticker_code in self.dashboard.purchase_info:
            if self.dashboard.new_csv:
                investment = round(self.avg_price * self.num_shares)
            else:
                investment = self.dashboard.purchase_info[self.ticker_code]['investment_value']
            return int(investment)

        else:
            investment = round(self.avg_price * self.num_shares)
            return int(investment)

    def get_present_value(self):
        present_value = round(self.get_today_data() * self.num_shares, 2)
        # present_value = round(self.dashboard.purchase_info[self.ticker_code]['last_fetched_price'] * self.num_shares)
        return int(present_value)
    
    def update_max_price_from_current(self):
        if self.last_fetched_price is not None:
            self.max_price = max(self.max_price, self.last_fetched_price)
            self.threshold_price = self.get_threshold_price()
        return self.max_price, self.threshold_price

    def process_historic_data_for_json(self, tail_length=10):
        historical_data_dict = self.historical_data.tail(tail_length).reset_index().rename(columns={'index': 'Date'}).to_dict(orient='records')
        keys_to_delete = ["Open", "Low", "Volume", "Dividends", "Stock Splits", "High"]
        for entry in historical_data_dict:
            entry['Date'] = entry['Date'].isoformat()
            for key in keys_to_delete:
                del entry[key]
        return historical_data_dict


    def add_to_dashboard_json(self):
        historical_data_dict = self.process_historic_data_for_json(tail_length=10)
        download_historic_info(self.ticker_code, self.suffix, self.purchase_date, output_folder="./data/stock_historic_data")

        self.dashboard.purchase_info[self.ticker_code] = {
            "suffix": self.suffix,
            "purchase_date": self.purchase_date,
            "num_shares": self.num_shares,
            "max_price": self.max_price,
            "threshold_percentage": self.threshold_percentage,
            "threshold_price": self.threshold_price,
            "average_price": self.avg_price,
            "investment_value": self.investment_val,
            "historic_data": historical_data_dict,
            "last_fetched_price": self.last_fetched_price,
            "last_fetched_time": self.last_fetched_time,
            "BUY": self.buy_threshold,
            "SELL": self.sell_threshold,
            "STATUS": self.status
        }
        
        self.dashboard.save_purchase_info(self.dashboard.purchase_info)

    def edit_threshold_percentage(self, new_threshold):
        # Update the threshold values
        self.threshold_percentage = new_threshold
        self.threshold_price = self.get_threshold_price()
        
        # Check if the ticker_code exists in the purchase_info
        if self.ticker_code in self.dashboard.purchase_info:
            # Update only the changed fields
            self.dashboard.purchase_info[self.ticker_code]['threshold_percentage'] = self.threshold_percentage
            self.dashboard.purchase_info[self.ticker_code]['threshold_price'] = self.threshold_price
            
            # Save the updated information
            self.dashboard.save_purchase_info(self.dashboard.purchase_info)
        else:
            print(f"Ticker code {self.ticker_code} not found in purchase_info.")

    def delete_stock(self):
        if self.ticker_code in self.dashboard.purchase_info:
            # stock_file_path = f"data/stock_historic_data/{self.ticker_code}_{self.suffix}.json"
            del self.dashboard.purchase_info[self.ticker_code]

            # also delete historic data file
            
            if os.path.exists(self.historic_file_path):
                os.remove(self.historic_file_path)
            else:
                print(f"The file {self.historic_file_path} does not exist")

            self.dashboard.save_purchase_info(self.dashboard.purchase_info)
        else:
            print(f"Ticker code {self.ticker_code} not found in purchase_info.")

    def edit_purchase_date(self, new_date):
        # Update the purchase date
        self.purchase_date = new_date
        self.historical_data = self.fetch_historical_data()
        self.max_price = self.get_max_price()
        self.threshold_price = self.get_threshold_price()

        # update stock historic data at self.historic_file_path

        download_historic_info(self.ticker_code, self.suffix, self.purchase_date, output_folder="./data/stock_historic_data")       
      
        # Check if the ticker_code exists in the purchase_info
        if self.ticker_code in self.dashboard.purchase_info:
            # Update only the changed fields
            self.dashboard.purchase_info[self.ticker_code]['purchase_date'] = self.purchase_date
            self.dashboard.purchase_info[self.ticker_code]['historic_data'] = self.process_historic_data_for_json(tail_length=10)
            
            self.dashboard.purchase_info[self.ticker_code]['max_price'] = self.max_price
            self.dashboard.purchase_info[self.ticker_code]['threshold_price'] = self.threshold_price
            
            # Save the updated information
            self.dashboard.save_purchase_info(self.dashboard.purchase_info)
        else:
            print(f"Ticker code {self.ticker_code} not found in purchase_info.")