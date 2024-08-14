import os
from datetime import datetime
from dateutil import tz
import pytz
import plotly.graph_objs as go
import pandas as pd


def format_to_indian_date(date):
    return datetime.strptime(date, '%Y-%m-%d').strftime('%d-%m-%Y')

def process_stock(stock):
    stock.update_data()
    stock.max_price, stock.threshold_price = stock.update_max_price_from_current()
    stock.add_to_dashboard_json()

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
        "Present Value": stock.present_val,
        "Gains": int(stock.present_val - stock.investment_val),
        "Gain %": ((stock.present_val - stock.investment_val) / stock.investment_val) * 100
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



def plot_data(historical_data, today_data, stock_name):
    fig = go.Figure()
    
    if not historical_data.empty:
        fig.add_trace(go.Scatter(
            x=historical_data.index,
            y=historical_data['Close'],
            mode='lines+markers',
            name=f'{stock_name} Historical Data',
            line=dict(color='blue', width=2),
            marker=dict(color='white', size=8, symbol='circle', line=dict(color='black', width=1))
        ))
        
        if not today_data.empty:
            prev_close = historical_data['Close'].iloc[-1]
            today_close = today_data['Close'].iloc[-1]
            
            line_color = 'red' if today_close < prev_close else 'green'
            
            fig.add_trace(go.Scatter(
                x=[historical_data.index[-1], convert_to_iso_format(str(today_data['last_fetched_time'].values[0]))],
                y=[prev_close, today_close],
                mode='lines+markers',
                name=f'{stock_name} Current Data',
                line=dict(color=line_color, width=2, dash='dot'),
                marker=dict(color=line_color)
            ))
    else:
        fig.add_trace(go.Scatter(
            x=[],
            y=[],
            mode='lines+markers',
            name=f'{stock_name} No Historical Data',
            line=dict(color='grey', width=2),
            marker=dict(color='grey')
        ))
    
    fig.update_layout(title=f'{stock_name}',
                      xaxis_title='Date',
                      yaxis_title='Price',
                      xaxis_rangeslider_visible=False,
                      template='plotly_dark',
                      height=400,
                      width=800,
                      showlegend=False)
    
    return fig

def process_new_csv_json(dashboard):
    # Read the new data from the CSV file
    new_data = dashboard.df

    new_stocks = set(new_data['Instrument'].unique())  
    existing_stocks = set(dashboard.purchase_info.keys())  
    # stocks_to_add = new_stocks - existing_stocks
    stocks_to_delete = [stock_code for stock_code in existing_stocks if stock_code not in new_stocks]
    common_stocks = existing_stocks & new_stocks

    # stocks_to_add = list(stocks_to_add)
    stocks_to_delete = list(stocks_to_delete)
    common_stocks = list(common_stocks)

    for stock_code in common_stocks:
        #check if Qty corresponding to the stock has changed, if yes then update
        if dashboard.purchase_info[stock_code]['num_shares'] != new_data[new_data['Instrument'] == stock_code]['Qty.'].values[0]:
            dashboard.purchase_info[stock_code]['num_shares'] = new_data[new_data['Instrument'] == stock_code]['Qty.'].values[0]

    for stock_code in stocks_to_delete:
        del dashboard.purchase_info[stock_code]
    
    return stocks_to_delete

import plotly.graph_objects as go

def plot_scatter_plot(dashboard):
    fig = go.Figure()

    x_values = []
    y_values = []
    marker_size = []
    colors = []
    stock_names = []

    min_size = 10
    max_size = 100  # Maximum marker size for the highest gain
    size_scale_factor = max_size / 700  # Scale to fit the range -100% to +600%

    for stock_code in dashboard.purchase_info:
        stock = dashboard.purchase_info[stock_code]
        x_values.append(str(stock_code))
        
        # Extract values from stock_objects
        present_val = stock["last_fetched_price"]*stock["num_shares"]
        investment_val = stock["investment_value"]
        gain_percent = ((present_val - investment_val) / investment_val) * 100
        
        y_values.append(float(gain_percent))
        stock_names.append(stock_code)
        
        # Set color based on whether gain_percent is positive or negative
        if gain_percent >= 0:
            colors.append('rgb(116, 252, 48)')  # Bright green
        else:
            colors.append('rgb(242, 15, 15)')  # Bright red
        
        # Calculate size based on gain percent, ensuring minimum size
        calculated_size = max(min_size, (abs(gain_percent)+50) * size_scale_factor)
        marker_size.append(calculated_size)

    fig.add_trace(go.Scatter(
        x=x_values,
        y=y_values,
        mode='markers',
        text=stock_names,  # Display stock names on hover
        marker=dict(
            size=marker_size,
            color=colors,  # Use discrete colors based on gain percent
            showscale=False,  # No need for color scale bar with discrete colors
            line=dict(color='rgba(0,0,0,0)', width=0)
        ),
        hoverinfo='text+x+y'  # Show stock names, x, and y values on hover
    ))

    fig.update_layout(
        title='Stocks Gain %',
        xaxis_title='Stock',
        yaxis_title='Gain %',
        template='plotly_dark',
        height=500,
        width=800
    )

    return fig