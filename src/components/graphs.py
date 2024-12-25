
import pandas as pd
import streamlit as st
import plotly.graph_objs as go
from utils.helpers import reverse_date_string, convert_to_iso_format


def plot_line_graph(historical_data, today_data, stock_name):
    fig = go.Figure()
    
    if not historical_data.empty:
        fig.add_trace(go.Scatter(
            x=historical_data.index,
            y=historical_data['Close'],
            mode='lines',
            # mode='lines+markers',
            # name=f'{stock_name} Historical Data',
            line=dict(color='blue', width=2),
            # marker=dict(color='white', size=8, symbol='circle', line=dict(color='black', width=1))
            # marker=dict(color='white', size=8, line=dict(color='black', width=1))

        ))
        
        if not today_data.empty:
            prev_close = historical_data['Close'].iloc[-1]
            today_close = today_data['Close'].iloc[-1]
            
            line_color = 'red' if today_close < prev_close else 'green'
            
            fig.add_trace(go.Scatter(
                x=[historical_data.index[-1], convert_to_iso_format(str(today_data['last_fetched_time'].values[0]))],
                y=[prev_close, today_close],
                mode='lines',
                # mode='lines+markers',
                # name=f'{stock_name} Current Data',
                line=dict(color=line_color, width=2, dash='dot'),
                # marker=dict(color=line_color)
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
    
    fig.update_layout(
                    # title=f'{stock_name}',
                    #   xaxis_title='Date',
                    #   yaxis_title='Price',
                      xaxis_rangeslider_visible=False,
                      template='plotly_dark',
                      height=150,
                      width=250,
                      showlegend=False,
                      margin=dict(l=0, r=0, t=0.5, b=0.5),
                      xaxis=dict(showline=False, zeroline=False, showgrid=False, ticks=""),
                    yaxis=dict(showline=False, zeroline=False, showgrid=False, ticks=""))
    
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

    # Fetch purchase information
    purchase_info = dashboard.get_purchase_info()

    if purchase_info:
        # Add a dropdown to select the sorting order
        col11, col12 = st.columns([1, 5])  # Adjust ratio (e.g., 1:4) to control dropdown width
        with col11:
            # Add a dropdown to select the sorting order
            sort_order = st.selectbox(
                "Sort stocks by:",
                options=["Alphabetical (A-Z)", "Reverse Alphabetical (Z-A)", "Purchase Date (Oldest First)", "Purchase Date (Newest First)"]
            )
        
        # Sort stocks based on user selection
        if sort_order == "Alphabetical (A-Z)":
            sorted_purchase_info = dict(sorted(purchase_info.items()))
        elif sort_order == "Reverse Alphabetical (Z-A)":
            sorted_purchase_info = dict(sorted(purchase_info.items(), reverse=True))
        elif sort_order == "Purchase Date (Oldest First)":
            sorted_purchase_info = dict(sorted(purchase_info.items(), key=lambda item: item[1]["purchase_date"]))
        elif sort_order == "Purchase Date (Newest First)":
            sorted_purchase_info = dict(sorted(purchase_info.items(), key=lambda item: item[1]["purchase_date"], reverse=True))


        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            st.write("**Stock**")
        with col2:
            st.write("**Purchase Date**")
        with col3:
            st.write("**Graph**")

        
        # Iterate through each stock and display them in rows
        for ticker_code, info in sorted_purchase_info.items():
            # Prepare historical and today data
            historical_data = pd.DataFrame(info['historic_data'])
            historical_data['Date'] = pd.to_datetime(historical_data['Date'])
            historical_data.set_index('Date', inplace=True)
            
            today_data = pd.DataFrame(columns=['Close', 'last_fetched_time'])
            today_data['Close'] = [info['last_fetched_price']]
            today_data['last_fetched_time'] = [(info['last_fetched_time'])]
            
            # Create a row with two columns for each stock
            col1, col2, col3 = st.columns([1, 1, 3])  # Adjust column width ratio (1:3 for better visuals)
            
            with col1:
                st.write(f"**{ticker_code}**")
            
            with col2:
                stock_purchase_date = reverse_date_string(info["purchase_date"])
                st.write(f"{stock_purchase_date}")

            with col3:
                fig = plot_line_graph(historical_data, today_data, ticker_code)
                st.plotly_chart(fig, use_container_width=False)

            st.markdown("<hr>", unsafe_allow_html=True)