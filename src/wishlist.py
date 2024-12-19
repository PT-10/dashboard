import streamlit as st
import pandas as pd
from utils import load_wishlist, save_wishlist, set_status
from classes import Wishlist_Stock
import time

def display_wishlist():
    wishlist_json_path = './data/wishlist.json'
    # Initialize session state variables
    if 'wishlist' not in st.session_state:
        st.session_state.wishlist = load_wishlist(wishlist_json_path)
    if 'wishlist_fetching' not in st.session_state:
        st.session_state.wishlist_fetching = False
    if 'wishlist_last_updated' not in st.session_state:
        st.session_state.wishlist_last_updated = None
    if 'wishlist_stock_objects' not in st.session_state:
        if st.session_state.wishlist:
            st.session_state.wishlist_stock_objects = {ticker: Wishlist_Stock(ticker, st.session_state.wishlist[ticker]['exchange']) for ticker in st.session_state.wishlist}
        else:
            st.session_state.wishlist_stock_objects = {}
    if 'wishlist_edit_mode' not in st.session_state:
        st.session_state.wishlist_edit_mode = False



    st.write('Wishlist')
    col1, col2, col3, colx, col4, col5 = st.columns([0.8, 0.5, 1, 1, 0.5, 0.5])

    with col1:
        # Input for ticker code
        ticker_code = st.text_input('Enter Ticker Code')
        #capitalize
        ticker_code = ticker_code.upper()

    with col2:
        # Dropdown for stock exchange
        exchange_options = ['NS', 'BO']
        selected_exchange = st.selectbox('Stock Exchange', exchange_options, index=0)

    with col4:
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
        default_refresh_rate = '2 hours'
        refresh_rate = st.selectbox('Refresh Rate', list(refresh_rate_options.keys()), index=list(refresh_rate_options.keys()).index(default_refresh_rate))
        refresh_interval = refresh_rate_options[refresh_rate]

    with col5:
        # Fetch/Pause button
        st.markdown("<br>", unsafe_allow_html=True)
        fetch_button_label = 'Pause' if st.session_state.wishlist_fetching else 'Fetch'
        fetch_button = st.button(fetch_button_label)

    if fetch_button:
        st.session_state.wishlist_fetching = not st.session_state.wishlist_fetching
        if st.session_state.wishlist_fetching:
            st.write(f"Fetching data every {refresh_rate}...")

    # Function to delete stock from wishlist
    def delete_stocks(selected_tickers):
        for ticker in selected_tickers:
            if ticker in st.session_state.wishlist:
                del st.session_state.wishlist[ticker]
                if ticker in st.session_state.wishlist_stock_objects:
                    del st.session_state.wishlist_stock_objects[ticker]
        save_wishlist(st.session_state.wishlist, wishlist_json_path)  # Save changes to JSON
        st.success(f'Selected stocks removed from wishlist!')

    if st.button('Add to Wishlist'):
        if ticker_code:
            if ticker_code not in st.session_state.wishlist:
                stock = Wishlist_Stock(ticker_code, selected_exchange)
                st.session_state.wishlist[ticker_code] = {
                    "current_price": stock.last_fetched_price,
                    "exchange": selected_exchange,
                    "BUY": "",
                    "SELL": "",
                    "STATUS": ""
                }
                st.session_state.wishlist_stock_objects[ticker_code] = stock  # Store the stock object
                save_wishlist(st.session_state.wishlist, wishlist_json_path)  # Save changes to JSON
                st.success(f'Stock {ticker_code} added to the wishlist!')
            else:
                st.warning('Stock already in wishlist.')
        else:
            st.warning('Please enter a ticker code.')

    # Display the wishlist as a DataFrame
    if st.session_state.wishlist:
        df_placeholder = st.empty()
        wishlist_df = pd.DataFrame.from_dict(st.session_state.wishlist, orient='index').reset_index()
        wishlist_df = wishlist_df.drop(columns=['exchange'])
        wishlist_df.rename(columns={'index': 'Ticker', 'current_price': 'Current Price'}, inplace=True)

        button_col1, button_col2, button_col3, button_col4 = st.columns([2, 2, 0.5, 0.5])

        # Add a delete column with icons
        if st.session_state.wishlist_edit_mode:
            wishlist_df['Delete'] = [False for _ in range(len(wishlist_df))]
        
        # Editable DataFrame
        edited_wishlist_df = df_placeholder.data_editor(wishlist_df, use_container_width=True, disabled=("Ticker", "Current Price", "STATUS"), hide_index=True)

        with button_col3:
            if st.button('Edit Wishlist' if not st.session_state.wishlist_edit_mode else 'Delete Stocks'):
                st.session_state.wishlist_edit_mode = not st.session_state.wishlist_edit_mode

                # If switching to delete mode, save any changes first
                if not st.session_state.wishlist_edit_mode:
                    selected_tickers = edited_wishlist_df[edited_wishlist_df['Delete']].Ticker.tolist()
                    if selected_tickers:
                        delete_stocks(selected_tickers)
                        save_wishlist(st.session_state.wishlist, wishlist_json_path)
                        
                        if st.session_state.wishlist:
                            del_wishlist_df = pd.DataFrame.from_dict(st.session_state.wishlist, orient='index').reset_index()
                            del_wishlist_df = del_wishlist_df.drop(columns=['exchange'])
                            del_wishlist_df.rename(columns={'index': 'Ticker', 'current_price': 'Current Price'}, inplace=True)

                            # Update the placeholder with the new DataFrame
                            df_placeholder.data_editor(del_wishlist_df, use_container_width=True, disabled=("Ticker", "Current Price", "STATUS"), hide_index=True)
                    
                        
                        st.success('Selected stocks removed from wishlist!')
                    else:
                        st.warning('No stocks selected for deletion.')

        with button_col4:
            if st.button('Save Changes'):
                for index, row in edited_wishlist_df.iterrows():
                    ticker = row['Ticker']
                    st.session_state.wishlist[ticker]['BUY'] = row['BUY']
                    st.session_state.wishlist[ticker]['SELL'] = row['SELL']
                    st.session_state.wishlist_stock_objects[ticker].buy_threshold = row['BUY']
                    st.session_state.wishlist_stock_objects[ticker].sell_threshold = row['SELL']

                    # Update the STATUS based on the current price
                    current_price = st.session_state.wishlist[ticker]['current_price']
                    buy_threshold = row['BUY']
                    sell_threshold = row['SELL'] 
                    st.session_state.wishlist[ticker]['STATUS'] = set_status(current_price, buy_threshold, sell_threshold)

                # Save updated wishlist after processing changes
                save_wishlist(st.session_state.wishlist, wishlist_json_path)

                # Display updated DataFrame
                updated_wishlist_df = pd.DataFrame.from_dict(st.session_state.wishlist, orient='index').reset_index()
                updated_wishlist_df = updated_wishlist_df.drop(columns=['exchange'])
                updated_wishlist_df.rename(columns={'index': 'Ticker', 'current_price': 'Current Price'}, inplace=True)

                # Update the placeholder with the new DataFrame
                df_placeholder.data_editor(updated_wishlist_df, use_container_width=True, disabled=("Ticker", "Current Price", "STATUS"), hide_index=True)
                # if st.button('Save Changes'):
                st.success('Changes saved!')


        # Fetching data if active
        if st.session_state.wishlist_fetching:
            def fetch_data():
                while st.session_state.wishlist_fetching:
                    with st.spinner('Fetching data...'):
                        for ticker_code in st.session_state.wishlist:
                            stock = st.session_state.wishlist_stock_objects.get(ticker_code)
                            if stock:  # Use existing stock object
                                # stock.update_price()  # Assume this method updates the stock price
                                st.session_state.wishlist[ticker_code]['current_price'] = stock.last_fetched_price

                                # Update STATUS based on the new current price
                                buy_threshold = st.session_state.wishlist[ticker_code]['BUY']
                                sell_threshold = st.session_state.wishlist[ticker_code]['SELL']
                                st.session_state.wishlist[ticker_code]['STATUS'] = set_status(stock.last_fetched_price, buy_threshold, sell_threshold)
                            else:
                                # Recreate stock object if not found (fallback)
                                stock = Wishlist_Stock(ticker_code, selected_exchange)
                                st.session_state.wishlist_stock_objects[ticker_code] = stock
                                st.session_state.wishlist[ticker_code]['current_price'] = stock.last_fetched_price

                                # Update STATUS for newly created stock
                                buy_threshold = st.session_state.wishlist[ticker_code]['BUY']
                                sell_threshold = st.session_state.wishlist[ticker_code]['SELL']
                                st.session_state.wishlist[ticker_code]['STATUS'] = set_status(stock.last_fetched_price, buy_threshold, sell_threshold)

                        # Save the updated wishlist to JSON
                        save_wishlist(st.session_state.wishlist, wishlist_json_path)
                    saved_wishlist_df = pd.DataFrame.from_dict(st.session_state.wishlist, orient='index').reset_index()
                    saved_wishlist_df = saved_wishlist_df.drop(columns=['exchange'])
                    saved_wishlist_df.rename(columns={'index': 'Ticker', 'current_price': 'Current Price'}, inplace=True)

                    # Update the placeholder with the new DataFrame
                    df_placeholder.data_editor(saved_wishlist_df, use_container_width=True, disabled=("Ticker", "Current Price", "STATUS"), hide_index=True, key='wishlist_df')
                    time.sleep(refresh_interval)

            # Start fetching data
            fetch_data()
    else:
        st.write("Your wishlist is empty.")