import streamlit as st
import pandas as pd
import os
import concurrent.futures
import time
from datetime import datetime
from utils import *
from classes import *
from wishlist import display_wishlist
from notifications import send_stock_notifications

def main():
    st.title('Stock Dashboard')
    json_file_path = './data/purchase_info.json'
    csv_file_path = None
    
    if os.path.exists('./data/meta_data.json'):
        with open('./data/meta_data.json', 'r') as file:
            #make dict object
            file_dict = json.load(file)
            last_key = list(file_dict.keys())[-1]
            if not file_dict[last_key]["All stocks added"]:
                csv_file_path = file_dict[last_key]["File"]

    dashboard = StockDashboard(json_file_path, csv_file_path)
    
    if 'uploaded' not in st.session_state:
        st.session_state.uploaded = None
        st.session_state.file_path = None

    # File uploader widget
    uploaded_file = st.file_uploader("Upload a file", type=["csv"])

    if uploaded_file is not None:
        # Save the uploaded file to the specified path
        upload_dir = 'uploads'
        os.makedirs(upload_dir, exist_ok=True)  # Create directory if it does not exist
        file_path = os.path.join(upload_dir, uploaded_file.name)
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Update the session state to reflect the uploaded file
        st.session_state.uploaded = True
        st.session_state.file_path = file_path

    if st.session_state.uploaded:
        # Display success message
        st.success("File uploaded successfully")

        # Process the uploaded file
        dashboard.csv_file_path = st.session_state.file_path
        dashboard.new_csv = True
        dashboard.process_new_csv()
        # process_new_csv_json(dashboard)

        # Display processing success message
        st.success("Data processed successfully")

        # Clear state to remove file uploader and messages
        st.session_state.uploaded = None
        st.session_state.file_path = None

    # Check if purchase_info.json is newly created
    is_new_file = not os.path.exists(json_file_path) or not bool(dashboard.get_purchase_info())

    # Initialize session state variables
    if 'fetching' not in st.session_state:
        st.session_state.fetching = False
    if 'stop_fetching' not in st.session_state:
        st.session_state.stop_fetching = False
    if 'last_updated' not in st.session_state:
        st.session_state.last_updated = None
    if 'visible_columns' not in st.session_state:
        st.session_state.visible_columns = [
            'Stock', 'Purchase Date', 'No. of Shares', 'Average Price', 'Max Price',
            'Threshold%', 'Threshold Price', 'Current Price', '% CP of Max' ,'Investment Value', 'Present Value',
            'Gains', 'Gain %', 'BUY', 'SELL', 'STATUS'
        ]
    if 'show_index' not in st.session_state:
        st.session_state.show_index = True

    if 'stock_objects' not in st.session_state:
        if is_new_file:
            st.session_state.stock_objects = {}
        else:
            purchase_info = dashboard.get_purchase_info()
            st.session_state.stock_objects = {ticker_code: Stock(ticker_code, info['purchase_date'], dashboard, info['threshold_percentage'], requires_fetching=False) for ticker_code, info in purchase_info.items()}
    
    tabs = st.tabs(['Dashboard', 'Graphs', 'Scatter Plot', 'Wishlist'])

    with tabs[0]:
        # Layout for refresh rate dropdown and buttons
        col1, col4, col2, col3 = st.columns([1, 5, 1, 1])

        with col1:
            refresh_rate_options = {
                '15 seconds': 15,
                '30 seconds': 30,
                '1 minute': 60,
                '5 minutes': 300,
                '10 minutes': 600,
                '20 minutes': 1200,
                '30 minutes': 1800,
                '1 hour': 3600,
                '2 hours': 7200,
                '4 hours': 14400
            }

            # Default value
            default_refresh_rate = '2 hours'

            # Selection box
            refresh_rate = st.selectbox('Select Refresh Rate', list(refresh_rate_options.keys()), index=list(refresh_rate_options.keys()).index(default_refresh_rate))

            # Retrieve the corresponding interval
            refresh_interval = refresh_rate_options[refresh_rate]
            
        with col2:
            # Button to start fetching data
            start_button = st.button('Start')

        with col3:
            # Button to stop fetching data
            stop_button = st.button('Stop')   

        # Initialize placeholders for table and last updated text
        summary_placeholder = st.empty()

        if 'edit_mode' not in st.session_state:
            st.session_state.edit_mode = False

        edit_box = st.checkbox('Edit Mode', value = st.session_state.edit_mode, key='edit_mode')

        table_placeholder = st.empty()
        last_updated_placeholder = st.empty()
        if is_new_file:
            st.write('Welcome! You need to add stocks to the dashboard.')
            if dashboard.get_holdings_data() is not None:
                # Add new stocks
                st.sidebar.header('Add New Stock')
                all_instruments = dashboard.get_holdings_data()['Instrument'].unique()
                selected_instrument = st.sidebar.selectbox('Select Stock', all_instruments)
                purchase_date = st.sidebar.date_input('Purchase Date', min_value=datetime(2000, 1, 1), max_value=datetime.today())
                threshold_percentage = st.sidebar.slider('Threshold Percentage', min_value=0, max_value=50, value=10)

                if st.sidebar.button('Add Stock'):
                    if selected_instrument:
                        purchase_date_str = purchase_date.strftime('%Y-%m-%d')  # Convert to yyyy-mm-dd format
                        stock = Stock(selected_instrument, purchase_date_str, dashboard, threshold_percentage, requires_fetching=True)
                        stock.add_to_dashboard_json()
                        #Add to stock_objects
                        st.session_state.stock_objects[selected_instrument] = stock

                        if len(dashboard.purchase_info) == len(all_instruments):
                            st.sidebar.success('All stocks added successfully.')
                        st.sidebar.success(f'Stock {selected_instrument} added successfully.')
                    else:
                        st.sidebar.warning('Please select a stock to add.')

        else:
            # Display existing stock data
            purchase_info = dashboard.get_purchase_info()
            if purchase_info:
                # stock_objects = {}
                futures = []
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    for ticker_code, info in purchase_info.items():
                        purchase_date = info['purchase_date']
                        threshold_percentage = info['threshold_percentage']
                        st.session_state.stock_objects[ticker_code] = Stock(ticker_code, purchase_date, dashboard, threshold_percentage, requires_fetching=False)
                        futures.append(executor.submit(process_stock, st.session_state.stock_objects[ticker_code]))

                results = []
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    results.append(result)

                df_results = pd.DataFrame(results)

                # Update the flag based on user interaction
                total_investment_value = df_results['Investment Value'].sum()
                total_present_value = df_results['Present Value'].sum()
                total_stocks = len(df_results)

                # Create a container for the summary cards
                with summary_placeholder.expander('Summary', expanded=True):
                    col1, col2, col3 = st.columns(3)
                    
                    # Card 1: Total Investment Value
                    with col1:
                        st.markdown(
                            f"""
                            <div style="background-color:rgba(240, 240, 240, 0.05); border-radius:10px; padding:20px; text-align:center; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">
                                <h6 style='margin-top:0;'>Total Investment Value</h6>
                                <h3>₹{total_investment_value:,.2f}</h3>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    
                    # Card 2: Total Present Value
                    with col2:
                        st.markdown(
                            f"""
                            <div style="background-color:rgba(240, 240, 240, 0.05); border-radius:10px; padding:20px; text-align:center; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">
                                <h6 style='margin-top:0;'>Total Present Value</h6>
                                <h3>₹{total_present_value:,.2f}</h3>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    
                    # Card 3: Total Number of Stocks
                    with col3:
                        st.markdown(
                            f"""
                            <div style="background-color:rgba(240, 240, 240, 0.05); border-radius:10px; padding:20px; text-align:center; box-shadow: 0px 4px 6px rgba(0,0,0,0.1); margin-bottom:15px;">
                                <h6 style='margin-top:0;'>Total Number of Stocks</h6>
                                <h3>{total_stocks}</h3>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                # Create a collapsible menu for managing columns
                with st.sidebar.expander('Manage Columns', expanded=False):
                    column_visibility = {
                        
                        'Purchase Date': 'Purchase Date',
                        'No. of Shares': 'No. of Shares',
                        'Average Price': 'Average Price',
                        'Max Price': 'Max Price',
                        'Threshold%': 'Threshold%',
                        'Threshold Price': 'Threshold Price',
                        'Current Price': 'Current Price',
                        '% CP of Max': '% CP of Max',
                        'Investment Value': 'Investment Value',
                        'Present Value': 'Present Value',
                        'Gains': 'Gains',
                        'Gain %': 'Gain %',
                        'BUY': 'BUY',
                        'SELL': 'SELL',
                        'STATUS': 'STATUS'
                    }

                    column_checks = {}
                    st.session_state.show_index = st.checkbox('Show Index', value=st.session_state.show_index)
                    for col_name in column_visibility:
                        column_checks[col_name] = st.checkbox(f'{col_name}', value=col_name in st.session_state.visible_columns)
                    # print(column_checks)
                    st.session_state.visible_columns = ['Stock']  # Always display these columns
                    st.session_state.visible_columns += [col for col, checked in column_checks.items() if checked]

                # Filter DataFrame based on visible columns
                visible_df = df_results[st.session_state.visible_columns]
                # Style DataFrame
                styled_df = style_dataframe(visible_df, df_results) 

                if 'display_df_results' not in st.session_state:
                    st.session_state.display_df_results = styled_df

                total_investment_value = df_results['Investment Value'].sum()
                total_present_value = df_results['Present Value'].sum()
                total_stocks = len(df_results)

                if st.session_state.edit_mode:
                    editable_columns = ['BUY', 'SELL']
                    disabled_columns = [col for col in styled_df.columns if col not in editable_columns]
                    
                    # Update the existing table placeholder
                    edited_data = st.data_editor(st.session_state.display_df_results, use_container_width=True, hide_index = not st.session_state.show_index, disabled=disabled_columns)
                    # print(edited_data)
                save_button = st.button('Save Changes', key='save_button')
                if save_button and st.session_state.edit_mode:
                    for index, row in edited_data.iterrows():
                        ticker_code = row['Stock']
                        buy_threshold = row['BUY']
                        sell_threshold = row['SELL'] 
                        current_price = dashboard.purchase_info[ticker_code]['last_fetched_price']

                        # print(f"Ticker Code: {ticker_code}, Buy: {buy_threshold}, Sell: {sell_threshold}")
                        dashboard.purchase_info[ticker_code]['BUY'] = buy_threshold
                        dashboard.purchase_info[ticker_code]['SELL'] = sell_threshold
                        st.session_state.stock_objects[ticker_code].buy_threshold = buy_threshold
                        st.session_state.stock_objects[ticker_code].sell_threshold = sell_threshold

                        status = set_status(current_price, buy_threshold, sell_threshold)

                        dashboard.purchase_info[ticker_code]['STATUS'] = status
                        st.session_state.stock_objects[ticker_code].status = status

                    dashboard.save_purchase_info(dashboard.purchase_info)

                    st.write('Changes saved successfully.')


                if not st.session_state.edit_mode:
                    # Update the existing table placeholder
                    disabled_columns = [col for col in styled_df.columns]
                    table_placeholder.data_editor(styled_df, use_container_width=True, hide_index = not st.session_state.show_index, disabled=disabled_columns)

                # Update last updated time
                last_updated_text = f"Last updated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                last_updated_placeholder.write(last_updated_text)

                # Allow user to add new stocks
                st.sidebar.header('Add New Stock')
                all_instruments = dashboard.get_holdings_data()['Instrument'].unique()
                existing_instruments = list(dashboard.purchase_info.keys())
                available_instruments = [inst for inst in all_instruments if inst not in existing_instruments]

                if available_instruments:
                    selected_instrument = st.sidebar.selectbox('Select Stock to Add', available_instruments)
                    purchase_date = st.sidebar.date_input('Purchase Date', min_value=datetime(2000, 1, 1), max_value=datetime.today())
                    threshold_percentage = st.sidebar.slider('Threshold Percentage', min_value=0, max_value=50, value=10)

                    if st.sidebar.button('Add Stock'):
                        if selected_instrument:
                            purchase_date_str = purchase_date.strftime('%Y-%m-%d')  # Convert to yyyy-mm-dd format
                            stock = Stock(selected_instrument, purchase_date_str, dashboard, threshold_percentage, requires_fetching=True)
                            st.session_state.stock_objects[ticker_code] = stock
                            stock.add_to_dashboard_json()
                            st.sidebar.success(f'Stock {selected_instrument} added successfully.')
                        else:
                            st.sidebar.warning('Please select a stock to add.')
                else:
                    st.sidebar.write('All stocks are already added.')

                # Add a horizontal line to separate sections
                st.sidebar.markdown('---')

                st.sidebar.header('Modify Stock')

                # Dropdown to choose between editing or deleting
                action = st.sidebar.selectbox('Choose Action', ['Edit Threshold Percentage', 'Edit Purchase Date', 'Delete Stock'])

                # Dropdown to select stock
                selected_instrument = st.sidebar.selectbox('Select Stock', existing_instruments)

                stock_object_update = st.session_state.stock_objects[selected_instrument]

                if action == 'Edit Threshold Percentage':
                    # Slider for editing threshold percentage
                    threshold_percentage = st.sidebar.slider(
                        'Update Threshold Percentage',
                        min_value=0,
                        max_value=50,
                        # value=dashboard.purchase_info[selected_instrument]['threshold_percentage']
                        value=10
                    )
                    
                    if st.sidebar.button('Edit Threshold Percentage'):
                        stock_object_update.edit_threshold_percentage(threshold_percentage)
                        st.sidebar.success(f'Threshold Percentage for {selected_instrument} updated successfully.')

                elif action == 'Edit Purchase Date':
                    # Date input for editing purchase date
                    purchase_date = st.sidebar.date_input(
                        'Update Purchase Date',
                        value=datetime.strptime(dashboard.purchase_info[selected_instrument]['purchase_date'], '%Y-%m-%d')
                    )
                    
                    if st.sidebar.button('Edit Purchase Date'):
                        purchase_date_str = purchase_date.strftime('%Y-%m-%d')
                        stock_object_update.edit_purchase_date(purchase_date_str)
                        st.sidebar.success(f'Purchase Date for {selected_instrument} updated successfully.')

                elif action == 'Delete Stock':
                    if st.sidebar.button('Delete Stock'):
                        stock_object_update.delete_stock()
                        st.sidebar.success(f'Stock {selected_instrument} deleted successfully.')

                # print(stock_objects)

            else:
                st.write('No stocks added to the dashboard.')         

        if start_button:
            
            st.session_state.fetching = True
            # st.session_state.stop_fetching = False
            st.write(f"Fetching data every {refresh_rate}...")
            print("Fetch button has been pressed", st.session_state.fetching)

            # def fetch_data():
            while st.session_state.fetching:
                print("Fetching session state", st.session_state.fetching)
                # if st.session_state.stop_fetching:
                #     st.session_state.fetching = False
                #     break
                
                with st.spinner('Fetching data...'):
                    futures = []

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        for ticker_code in dashboard.df['Instrument']:
                            if ticker_code not in dashboard.purchase_info:
                                continue
                            purchase_date = dashboard.purchase_info[ticker_code]['purchase_date']
                            threshold_percentage = dashboard.purchase_info[ticker_code]['threshold_percentage']
                            # st.session_state.stock_objects[ticker_code] = Stock(ticker_code, purchase_date, dashboard, threshold_percentage, requires_fetching=True)
                            futures.append(executor.submit(process_fetched_stock_data, st.session_state.stock_objects[ticker_code]))

                    results = []
                    for future in concurrent.futures.as_completed(futures):
                        result = future.result()
                        results.append(result)

                    df_results = pd.DataFrame(results)
                    print(df_results.columns)

                    #check which rows have the column 'STATUS' != 'PREV STATUS'
                    stocks_with_updated_status_df = df_results[df_results['STATUS'] != df_results['PREV STATUS']]
                    send_stock_notifications(stocks_with_updated_status_df)
                    
                    # Filter DataFrame based on visible columns
                    visible_df = df_results[st.session_state.visible_columns]
                    
                    # Style DataFrame
                    styled_df = style_dataframe(visible_df, df_results)

                    editable_columns = []
                    disabled_columns = [col for col in styled_df.columns if col not in editable_columns]
                    
                    # Update the existing table placeholder
                    table_placeholder.data_editor(styled_df, use_container_width=True, hide_index = not st.session_state.show_index, disabled=disabled_columns)
                    
                    # Update last updated time
                    last_updated_text = f"Last updated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    last_updated_placeholder.write(last_updated_text)
                    
                time.sleep(refresh_interval)
            
            # Start fetching data
            # fetch_data()

        if stop_button:
            st.session_state.fetching = False
            print("Stop button has been pressed", st.session_state.fetching)
            
            # st.session_state.stop_fetching = True
    
    with tabs[1]:
        
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
                    fig = plot_data(historical_data, today_data, ticker_code)
                    st.plotly_chart(fig, use_container_width=False)

                st.markdown("<hr>", unsafe_allow_html=True)


    with tabs[2]:
        #scatter plot
        st.write('Scatter Plot')
        figure = plot_scatter_plot(dashboard)
        st.plotly_chart(figure, use_container_width=True)

    with tabs[3]:
        display_wishlist()

if __name__ == "__main__":
    st.set_page_config(page_title="Stock Dashboard", layout="wide")

    main()
