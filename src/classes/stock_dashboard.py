import os
import json
import pandas as pd
from datetime import datetime

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
        if not os.path.exists('./data/meta_data.json'):
            self.first_time = True
            with open('./data/meta_data.json', 'w') as f:
                json.dump({}, f, indent=4)

        else:
            with open('./data/meta_data.json', 'r') as f:
                return json.load(f)
            
    def save_meta_data(self):
        with open('./data/meta_data.json', 'w') as f:
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
            suffix = self.purchase_info[stock_code]["suffix"]
            if os.path.exists(f"data/stock_historic_data/{stock_code}_{suffix}.json"):
                os.remove(f"data/stock_historic_data/{stock_code}_{suffix}.json")
            else:
                print(f"The file ./data/stock_historic_data/{stock_code}_{suffix}.json does not exist")
                continue

            del self.purchase_info[stock_code]

        for stock_code in common_stocks:
            new_qty = self.df[self.df['Instrument'] == stock_code]['Qty.'].values[0]
            new_num_shares = self.df[self.df['Instrument'] == stock_code]['Avg. cost'].values[0]

            shares_bool = self.purchase_info[stock_code]['num_shares'] != new_qty
            avg_price_bool = self.purchase_info[stock_code]['average_price'] != new_num_shares

            #check if Qty corresponding to the stock has changed, if yes then update
            if shares_bool:
                self.purchase_info[stock_code]['num_shares'] = int(new_qty)
        
            #check if average price corresponding to the stock has changed, if yes then update  
            if avg_price_bool:
                self.purchase_info[stock_code]['average_price'] = new_num_shares
            
            if shares_bool or avg_price_bool:
                self.purchase_info[stock_code]['investment_value'] = (new_qty)*(new_num_shares)
        return self.purchase_info
    
    # def process_new_csv_json(self):
    #     # Read the new data from the CSV file
    #     new_data = self.df

    #     new_stocks = set(new_data['Instrument'].unique())  
    #     existing_stocks = set(self.purchase_info.keys())  
    #     # stocks_to_add = new_stocks - existing_stocks
    #     stocks_to_delete = [stock_code for stock_code in existing_stocks if stock_code not in new_stocks]
    #     common_stocks = existing_stocks & new_stocks

    #     # stocks_to_add = list(stocks_to_add)
    #     stocks_to_delete = list(stocks_to_delete)
    #     common_stocks = list(common_stocks)

    #     for stock_code in common_stocks:
    #         #check if Qty corresponding to the stock has changed, if yes then update
    #         if self.purchase_info[stock_code]['num_shares'] != new_data[new_data['Instrument'] == stock_code]['Qty.'].values[0]:
    #             self.purchase_info[stock_code]['num_shares'] = new_data[new_data['Instrument'] == stock_code]['Qty.'].values[0]

    #     for stock_code in stocks_to_delete:
    #         del self.purchase_info[stock_code]
        
    #     return stocks_to_delete