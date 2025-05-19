import json
import pandas as pd
import plotly.graph_objs as go
import streamlit as st
from utils.helpers import reverse_date_string, convert_to_iso_format

def plot_small_scale_line_graph(historical_data, today_data, stock_name):
    fig = go.Figure()
    
    if not historical_data.empty:
        fig.add_trace(go.Scatter(
            x=historical_data.index,
            y=historical_data['Close'],
            mode='lines',
            line=dict(color='blue', width=2),
        ))
        
        if not today_data.empty:
            prev_close = historical_data['Close'].iloc[-1]
            today_close = today_data['Close'].iloc[-1]
            
            line_color = 'red' if today_close < prev_close else 'green'
            
            fig.add_trace(go.Scatter(
                x=[historical_data.index[-1], convert_to_iso_format(str(today_data['last_fetched_time'].values[0]))],
                y=[prev_close, today_close],
                mode='lines',
                line=dict(color=line_color, width=2, dash='dot'),
            ))
    else:
        fig.add_trace(go.Scatter(
            x=[],
            y=[],
            name=f'{stock_name} No Historical Data',
            line=dict(color='grey', width=2),
            marker=dict(color='grey')
        ))
    
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        template='plotly_dark',
        height=150,
        width=250,
        showlegend=False,
        margin=dict(l=1, r=0, t=0.5, b=0.5),
        xaxis=dict(showline=False, zeroline=False, showgrid=False, ticks=""),
        yaxis=dict(showline=False, zeroline=False, showgrid=False, ticks="")
    )
    
    return fig

# Change @st.cache_data to @st.cache_resource
@st.cache_resource(ttl=36000, show_spinner=True)
def load_stock_data(stock_data_json_path):
    with open(stock_data_json_path, 'r') as file:
        return json.load(file)

# Updated function without asyncio.run
@st.cache_resource(ttl=36000, show_spinner=True)
def plot_historic_line_graph(stock_symbol, stock_data_json_path):
    historical_data = load_stock_data(stock_data_json_path)
    
    if historical_data:
        # Create a DataFrame directly from the data
        df = pd.DataFrame(
            list(historical_data.items()), columns=['Date', 'Close']
        )
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values(by='Date')
        
        # Create the plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['Date'],
            y=df['Close'],
            line=dict(color='blue', width=2),
        ))
    else:
        # If no data exists, return an empty plot with a "No Data" message
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[],
            y=[],
            name=f'{stock_symbol} No Historical Data',
            line=dict(color='grey', width=2),
            marker=dict(color='grey')
        ))

    # Update layout to match the small-scale graph style
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        template='plotly_dark',
        height=150,
        showlegend=False,
        margin=dict(l=0, r=1, t=0.5, b=0.5),
        xaxis=dict(showline=False, zeroline=False, showgrid=False, ticks=""),
        yaxis=dict(showline=False, zeroline=False, showgrid=False, ticks=""),
    )

    return fig



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
        height=600,
        width=800
    )

    return fig


def display_price_graphs(dashboard):
    st.write('Historical Stock Prices')

    purchase_info = dashboard.get_purchase_info()

    if purchase_info:
        # Add a dropdown to select the sorting order
        col11, col12 = st.columns([1, 5])  # Adjust ratio (e.g., 1:4) to control dropdown width
        with col11:
            sort_order = st.selectbox(
                "Sort stocks by:",
                options=["A-Z", "Z-A", "Oldest Purchase", "Newest Purchase"]
            )
        
        # Sort stocks based on user selection
        if sort_order == "A-Z":
            sorted_purchase_info = dict(sorted(purchase_info.items()))
        elif sort_order == "Z-A":
            sorted_purchase_info = dict(sorted(purchase_info.items(), reverse=True))
        elif sort_order == "Oldest Purchase":
            sorted_purchase_info = dict(sorted(purchase_info.items(), key=lambda item: item[1]["purchase_date"]))
        elif sort_order == "Newest Purchase":
            sorted_purchase_info = dict(sorted(purchase_info.items(), key=lambda item: item[1]["purchase_date"], reverse=True))

        col1, col2, col3, col4 = st.columns([0.8, 0.8, 2, 1])
        with col1:
            st.write("**Stock**")
        with col2:
            st.write("**Purchase Date**")
        with col3:
            st.write("**Historic Graph**")
        with col4:
            st.write("**15 Days Graph**")

        # Iterate through each stock and display them in rows
        for ticker_code, info in sorted_purchase_info.items():
            historical_data = pd.DataFrame(info['historic_data'])
            historical_data['Date'] = pd.to_datetime(historical_data['Date'])
            historical_data.set_index('Date', inplace=True)
            
            today_data = pd.DataFrame(columns=['Close', 'last_fetched_time'])
            today_data['Close'] = [info['last_fetched_price']]
            today_data['last_fetched_time'] = [(info['last_fetched_time'])]
            
            # Create a row with two columns for each stock
            col1, col2, col3, col4 = st.columns([0.8, 0.8, 2, 1])  # Adjust column width ratio (1:3 for better visuals)
            
            with col1:
                st.write(f"**{ticker_code}**")
            
            with col2:
                stock_purchase_date = reverse_date_string(info["purchase_date"])
                st.write(f"{stock_purchase_date}")

            with col3:
                suffix = info['suffix']
                fig = plot_historic_line_graph(ticker_code, f"data/stock_historic_data/{ticker_code}_{suffix}.json")
                st.plotly_chart(fig, use_container_width=True)

            with col4:
                fig1 = plot_small_scale_line_graph(historical_data, today_data, ticker_code)
                st.plotly_chart(fig1, use_container_width=False)

            st.markdown("<hr>", unsafe_allow_html=True)
