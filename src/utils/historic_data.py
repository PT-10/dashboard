import os
import json
import yfinance as yf
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

def download_historic_info(stock_symbol, suffix, purchase_date, output_folder):
    ticker = f"{stock_symbol}.{suffix}"

    # Download the stock data starting from the purchase date
    data = yf.download(ticker, start=purchase_date)

    # Extract only the 'Close' prices and convert to dictionary with string dates
    closing_prices = data['Close']
    closing_prices = closing_prices.to_dict()
    closing_prices = {str(date): price for date, price in closing_prices.items()}

    # Define the output file path
    output_file = os.path.join(output_folder, f"{stock_symbol}_{suffix}.json")

    # Save the closing prices data to a JSON file
    with open(output_file, 'w') as f:
        json.dump(closing_prices, f, indent=4)

    # Print a message indicating the data has been downloaded for the stock
    print(f"Downloaded data for {stock_symbol} stock")


# Thread-safe print
print_lock = threading.Lock()

# Function to update individual stock data
def update_single_stock(file_path, stock_symbol, suffix, today):
    ticker = f"{stock_symbol}.{suffix}"
    try:
        # Fetch today's stock price using yfinance
        stock_data = yf.Ticker(ticker).history(period='1d')
        if not stock_data.empty:
            today_data = stock_data['Close'].values[0]  # Get the 'Close' price for today

            # Load existing data from the JSON file
            with open(file_path, 'r') as f:
                data = json.load(f)

            # Add today's data to the existing data
            data[today] = today_data

            # Save the updated data back to the file
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)

            with print_lock:
                print(f"Updated {ticker} with today's data ({today}: {today_data})")
        else:
            with print_lock:
                print(f"No data available for {ticker} on {today}")
    except Exception as e:
        with print_lock:
            print(f"Error updating {ticker}: {e}")

# Main function to update historic data
def update_historic_data():
    output_folder = './data/stock_historic_data'
    today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Today's date in YYYY-MM-DD format

    files = os.listdir(output_folder)
    # Prepare a list of arguments for each stock file
    tasks = []

    for file in files:
        file_path = os.path.join(output_folder, file)
        stock_symbol = file.split('_')[0]
        suffix = file.split('_')[1].split('.')[0]  # Extract the suffix if needed

        tasks.append((file_path, stock_symbol, suffix, today))

    # Using ThreadPoolExecutor to run updates concurrently
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(update_single_stock, *task) for task in tasks]

        # Wait for all futures to complete
        for future in as_completed(futures):
            pass  # Optionally, handle result or exception if needed

    print(f"Finished updating all stocks on {today}")



# # Folder to save the stock data
# output_folder = './data/stock_historic_data'

# # Ensure the folder exists
# if not os.path.exists(output_folder):
#     os.makedirs(output_folder)

# # # Read stock data from purchase_info.json file
# with open('./data/purchase_info.json', 'r') as file:
#     stock_data = json.load(file)

# # # Loop through each stock in the data
# for stock_symbol, info in stock_data.items():
#     output_folder = './data/stock_historic_data'
#     ticker = f"{stock_symbol}.{info['suffix']}"
#     purchase_date = info['purchase_date']
    
#     # Download the stock data starting from the purchase date
#     data = yf.download(ticker, start=purchase_date)

#     # Extract only the 'Close' prices and convert to dictionary with string dates
#     closing_prices = data['Close']
#     closing_prices = closing_prices.to_dict()
#     closing_prices = {str(date): price for date, price in closing_prices.items()}
    
#     # Define the output file path
#     output_file = os.path.join(output_folder, f"{stock_symbol}_{info['suffix']}.json")

#     # Save the closing prices data to a JSON file
#     with open(output_file, 'w') as f:
#         json.dump(closing_prices, f, indent=4)

#     # Print a message indicating the data has been downloaded for the stock
#     print(f"Downloaded data for {stock_symbol} stock")