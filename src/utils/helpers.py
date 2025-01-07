import os
import pytz
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def format_to_indian_date(date):
    return datetime.strptime(date, '%Y-%m-%d').strftime('%d-%m-%Y')

def process_stock(stock):
    # stock.update_data()
    # stock.max_price, stock.threshold_price = stock.update_max_price_from_current()
    # stock.add_to_dashboard_json()

    return {
        "Stock": stock.ticker_code,
        "Purchase Date": stock.purchase_date,
        "No. of Shares": stock.num_shares,
        "Average Price": stock.avg_price,
        "Max Price": stock.max_price,
        "Threshold%": stock.threshold_percentage,
        "Threshold Price": stock.threshold_price,
        "Current Price": stock.last_fetched_price,
        "% CP of Max": ((stock.last_fetched_price - stock.max_price) / stock.max_price) * 100,
        "Investment Value": stock.investment_val,
        "Present Value": round(stock.present_val,2),
        "Gains": int(stock.present_val - stock.investment_val),
        "Gain %": ((stock.present_val - stock.investment_val) / stock.investment_val) * 100,
        'BUY': stock.buy_threshold,
        'SELL': stock.sell_threshold,
        'STATUS': stock.status
    }

def process_fetched_stock_data(stock):
    # logging.info(f"Processing data for {stock.ticker_code}.")
    # logging.info(f"Initializing {stock.ticker_code} for fetching.")
    prev_status = stock.status
    prev_price = stock.last_fetched_price
    prev_last_fetched_time = stock.last_fetched_time
    
    stock.update_data()
    stock.max_price, stock.threshold_price = stock.update_max_price_from_current()
    stock.status = set_status(stock.last_fetched_price, stock.buy_threshold, stock.sell_threshold)
    if stock.last_fetched_price == None:
        stock.last_fetched_price = prev_price
        stock.last_fetched_time = prev_last_fetched_time
        
    stock.add_to_dashboard_json(fetch_historic_data=False)
    logging.info(f"Data fetched for {stock.ticker_code}: {stock.last_fetched_price}")
    
    return {
        "Stock": stock.ticker_code,
        "Purchase Date": stock.purchase_date,
        "No. of Shares": stock.num_shares,
        "Average Price": stock.avg_price,
        "Max Price": stock.max_price,
        "Threshold%": stock.threshold_percentage,
        "Threshold Price": stock.threshold_price,
        "Current Price": stock.last_fetched_price,
        "% CP of Max": ((stock.last_fetched_price - stock.max_price) / stock.max_price) * 100,
        "Investment Value": stock.investment_val,
        "Present Value": round(stock.present_val,2),
        "Gains": int(stock.present_val - stock.investment_val),
        "Gain %": ((stock.present_val - stock.investment_val) / stock.investment_val) * 100,
        'BUY': stock.buy_threshold,
        'SELL': stock.sell_threshold,
        'STATUS': stock.status,
        'PREV STATUS': prev_status
    }

def convert_to_iso_format(date_str, timezone_str='Asia/Kolkata'):
    # Define the local timezone
    local_tz = pytz.timezone(timezone_str)

    # Parse the input datetime string into a datetime object
    local_time = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')

    # Localize the datetime object to the specified timezone
    local_time = local_tz.localize(local_time)
    
    # Convert to ISO 8601 format with timezone information
    iso_format_time = local_time.isoformat()
    
    return iso_format_time

def reverse_date_string(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d').strftime('%d-%m-%Y')

def format_price(price, threshold_price):
    return 'color: rgba(34, 188, 88);' if price > threshold_price else 'color: red;'

def format_gain_percentage(gain_percentage):
    return 'color: rgba(34, 188, 88);' if gain_percentage > 0 else 'color: red;'

def style_dataframe(df, df_results):
    # Apply conditional formatting to the DataFrame
    def style_current_price(value, index):
        # Check if both columns exist before accessing them
        threshold_price = df_results['Threshold Price'][index]
        return format_price(value, threshold_price)

    def style_gain_percentage(value):
        return format_gain_percentage(float(value))

    # Apply 2f precision formatting to relevant columns
    df_styled = df.style.format({
        "Purchase Date": format_to_indian_date,
        "Average Price": "{:.2f}",
        "Max Price": "{:.2f}",
        "Present Value": "{:.0f}",
        "Threshold Price": "{:.2f}",
        "Current Price": "{:.2f}",
        "% CP of Max": "{:.2f}",
        "Gain %": "{:.2f}"
    })

    # Apply styles to DataFrame
    #check if the column is present in the dataframe
    if 'Current Price' in df.columns:
        df_styled = df_styled.applymap(lambda value: style_current_price(value, df[df['Current Price'] == value].index[0]), subset=['Current Price'])
    if 'Gain %' in df.columns:
        df_styled = df_styled.applymap(style_gain_percentage, subset=['Gain %'])
    if 'Gains' in df.columns:
        df_styled = df_styled.applymap(lambda x: 'color: red;' if x < 0 else 'color: rgba(34, 188, 88);', subset=['Gains'])

    return df_styled

def set_status(last_fetched_price, buy_threshold, sell_threshold):
        # print(f"last_fetched_price: {last_fetched_price}, buy_threshold: {buy_threshold}, sell_threshold: {sell_threshold}")
        if buy_threshold:
            if float(last_fetched_price) <= float(buy_threshold):
                return "BUY" 
        if sell_threshold:
            if float(last_fetched_price) >= float(sell_threshold):
                return "SELL"
        if buy_threshold and sell_threshold:
            if float(buy_threshold) < float(last_fetched_price) < float(sell_threshold):
                return ""

        return ""

