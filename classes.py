import pandas as pd
import json
import os
import yfinance as yf
from datetime import datetime
import logging

def process_historic_data_for_json(historical_data, tail_length=10):
    historical_data_dict = historical_data.tail(tail_length).reset_index().rename(columns={'index': 'Date'}).to_dict(orient='records')
    keys_to_delete = ["Open", "Low", "Volume", "Dividends", "Stock Splits", "High"]
    for entry in historical_data_dict:
        entry['Date'] = entry['Date'].isoformat()
        for key in keys_to_delete:
            del entry[key]
    return historical_data_dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class StockDashboard:
    def __init__(self, json_file_path, csv_file_path):
        self.json_file_path = json_file_path
        self.csv_file_path = csv_file_path
        self.new_csv = False
        self.purchase_info = self.load_purchase_info()
        self.df = pd.read_csv(self.csv_file_path) if self.csv_file_path else None
        self.meta_data = None
        self.first_time = False
        
    def load_meta_data(self):
        if not os.path.exists('meta_data.json'):
            self.first_time = True
            with open('meta_data.json', 'w') as f:
                json.dump({}, f, indent=4)

        else:
            with open('meta_data.json', 'r') as f:
                return json.load(f)
            
    def save_meta_data(self):
        with open('meta_data.json', 'w') as f:
            json.dump(self.meta_data, f, indent=4)

    def save_purchase_info(self, purchase_info):
        with open(self.json_file_path, 'w') as f:
            json.dump(purchase_info, f, indent=4)

    def ensure_json_file(self):
        if not os.path.exists(self.json_file_path):
            self.save_purchase_info({})
    def load_purchase_info(self):
        self.ensure_json_file()
        if os.path.exists(self.json_file_path):
            with open(self.json_file_path, 'r') as f:
                return json.load(f)
        return {}

    
    def get_holdings_data(self):
        return self.df

    def get_purchase_info(self):
        return self.purchase_info
    
    def process_new_csv(self):
        #check if purchase_json exists
        #if purchase_json exists then we need to update data else data needs to be added afresh
        self.df = pd.read_csv(self.csv_file_path)
        self.meta_data = self.load_meta_data()

        if self.new_csv:
            if self.first_time:
                length = 0
                self.meta_data = {"file0": {"File": self.csv_file_path,"Date added": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                   "Number of Stocks": len(self.df['Instrument']),
                                   "All stocks added": False}}
            else:
                length = len(self.meta_data)

            #use the key as file0 file1 and so on
            key = f"file{length}"
            #if it is a new csv, then add file_path and time of adding to the meta_data
            self.meta_data[key] = {"File": self.csv_file_path,
                                   "Date added": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                   "Number of Stocks": len(self.df['Instrument']),
                                   "All stocks added": False}
            #save the meta_data
            self.save_meta_data()
        self.update_purchase_info()
        self.save_purchase_info(self.purchase_info)

    def update_purchase_info(self):
        new_stocks = set(self.df['Instrument'].unique())  
        existing_stocks = set(self.purchase_info.keys())  
        # stocks_to_add = new_stocks - existing_stocks
        stocks_to_delete = [stock_code for stock_code in existing_stocks if stock_code not in new_stocks]
        common_stocks = existing_stocks & new_stocks

        # stocks_to_add = list(stocks_to_add)
        stocks_to_delete = list(stocks_to_delete)
        common_stocks = list(common_stocks)

        for stock_code in stocks_to_delete:
            del self.purchase_info[stock_code]

        for stock_code in common_stocks:
            #check if Qty corresponding to the stock has changed, if yes then update
            if self.purchase_info[stock_code]['num_shares'] != self.df[self.df['Instrument'] == stock_code]['Qty.'].values[0]:
                self.purchase_info[stock_code]['num_shares'] = int(self.df[self.df['Instrument'] == stock_code]['Qty.'].values[0])
        
            #check if average price corresponding to the stock has changed, if yes then update  
            if self.purchase_info[stock_code]['average_price'] != self.df[self.df['Instrument'] == stock_code]['Avg. cost'].values[0]:
                self.purchase_info[stock_code]['average_price'] = self.df[self.df['Instrument'] == stock_code]['Avg. cost'].values[0]

        return self.purchase_info   



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
        present_value = round(self.get_today_data() * self.num_shares)
        # present_value = round(self.dashboard.purchase_info[self.ticker_code]['last_fetched_price'] * self.num_shares)
        return int(present_value)
    
    def update_max_price_from_current(self):
        if self.last_fetched_price is not None:
            self.max_price = max(self.max_price, self.last_fetched_price)
            self.threshold_price = self.get_threshold_price()
        return self.max_price, self.threshold_price
    
    def historical_data_rolling_window_update(self):
        today_data_dict = self.yfticker.history(period='1d')
        keys_to_delete = ["Open", "Low", "Volume", "Dividends", "Stock Splits", "High"]
        for entry in today_data_dict:
            entry['Date'] = entry['Date'].isoformat()
            for key in keys_to_delete:
                del entry[key]
        historical_data_json = self.dashboard.purchase_info[self.ticker_code]['historic_data']
        historical_data_json = historical_data_json[1:].append(today_data_dict, ignore_index=True)   
    def add_to_dashboard_json(self):
        historical_data_dict = process_historic_data_for_json(self.historical_data, tail_length=10)

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
            "last_fetched_time": self.last_fetched_time
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
            del self.dashboard.purchase_info[self.ticker_code]
            self.dashboard.save_purchase_info(self.dashboard.purchase_info)
        else:
            print(f"Ticker code {self.ticker_code} not found in purchase_info.")

    def edit_purchase_date(self, new_date):
        # Update the purchase date
        self.purchase_date = new_date
        self.historical_data = self.fetch_historical_data()
        self.max_price = self.get_max_price()
        self.threshold_price = self.get_threshold_price()
        
        # Check if the ticker_code exists in the purchase_info
        if self.ticker_code in self.dashboard.purchase_info:
            # Update only the changed fields
            self.dashboard.purchase_info[self.ticker_code]['purchase_date'] = self.purchase_date
            self.dashboard.purchase_info[self.ticker_code]['historic_data'] = process_historic_data_for_json(self.historical_data, tail_length=10)
            
            self.dashboard.purchase_info[self.ticker_code]['max_price'] = self.max_price
            self.dashboard.purchase_info[self.ticker_code]['threshold_price'] = self.threshold_price
            
            # Save the updated information
            self.dashboard.save_purchase_info(self.dashboard.purchase_info)
        else:
            print(f"Ticker code {self.ticker_code} not found in purchase_info.")

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

