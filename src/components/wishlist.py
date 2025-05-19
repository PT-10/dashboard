import os
import time
import json
import pandas as pd
import streamlit as st
from classes.wishlist_stock import Wishlist_Stock
from utils.helpers import set_status
import concurrent.futures
import logging
from utils.notifications import send_stock_notifications

def load_wishlist(json_file_path):
    if not os.path.exists(json_file_path):
            with open(json_file_path, 'w') as f:
                json.dump({}, f, indent=4)

    if os.path.exists(json_file_path):
        with open(json_file_path, 'r') as f:
            return json.load(f)


def save_wishlist(wishlist, json_file_path):
    with open(json_file_path, 'w') as f:
        json.dump(wishlist, f, indent=4)




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

    def fetch_and_update_wishlist_stock(ticker_code, stock, buy_threshold, sell_threshold):
        stock.get_today_data()
        last_price = stock.last_fetched_price
        status = set_status(last_price, buy_threshold, sell_threshold)
        return ticker_code, last_price, status

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
        default_refresh_rate = '2 hours'
        refresh_rate = st.selectbox('Refresh Rate', list(refresh_rate_options.keys()), index=list(refresh_rate_options.keys()).index(default_refresh_rate))
        refresh_interval = refresh_rate_options[refresh_rate]

    with col2:
        # Button to start fetching data
        start_button = st.button('Start', key="wishlist_start")

    with col3:
        # Button to stop fetching data
        stop_button = st.button('Stop', key="wishlist_stop") 

    if start_button:
        st.session_state.wishlist_fetching = True
        st.write(f"Fetching data every {refresh_rate}...")  # e.g., "every 30 seconds"
        print("Fetch button has been pressed in wishlist", st.session_state.wishlist_fetching)

        while st.session_state.wishlist_fetching:
            print("Wishlist fetching session state:", st.session_state.wishlist_fetching)
            with st.spinner('Fetching data...'):
                futures = []
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    for ticker_code in st.session_state.wishlist:
                        stock = st.session_state.wishlist_stock_objects.get(ticker_code)
                        if not stock:
                            exchange = st.session_state.wishlist[ticker_code]['exchange']
                            stock = Wishlist_Stock(ticker_code, exchange)
                            st.session_state.wishlist_stock_objects[ticker_code] = stock

                        buy_threshold = st.session_state.wishlist[ticker_code]['BUY']
                        sell_threshold = st.session_state.wishlist[ticker_code]['SELL']
                        futures.append(
                            executor.submit(
                                fetch_and_update_wishlist_stock,
                                ticker_code, stock, buy_threshold, sell_threshold
                            )
                        )

                # Gather results and update session state in the main thread
                for future in concurrent.futures.as_completed(futures):
                    ticker_code, last_price, status = future.result()
                    st.session_state.wishlist[ticker_code]['current_price'] = last_price
                    st.session_state.wishlist[ticker_code]['STATUS'] = status
                    logging.info(f"Data fetched for {ticker_code}: {last_price}")

                # Save the updated wishlist to JSON
                save_wishlist(st.session_state.wishlist, wishlist_json_path)

            # Display the updated wishlist
            saved_wishlist_df = pd.DataFrame.from_dict(st.session_state.wishlist, orient='index').reset_index()
            saved_wishlist_df = saved_wishlist_df.drop(columns=['exchange'])
            saved_wishlist_df.rename(columns={'index': 'Ticker', 'current_price': 'Current Price'}, inplace=True)
            st.dataframe(saved_wishlist_df, use_container_width=True)

            time.sleep(refresh_interval)  # Pause before next fetch cycle

    if stop_button:
            st.session_state.fetching = False
            print("Stop button has been pressed in wishlist", st.session_state.wishlist_fetching)

    mode = st.radio("Select Mode", ["Normal Mode", "Edit Mode"], index=0)

    if mode == "Edit Mode":
        st.subheader("➕ Add New Stock")
        with st.form("add_stock", clear_on_submit=True):
            ticker_code = st.text_input("Enter Ticker (e.g., RELIANCE)")
            ticker_code = ticker_code.upper()
            selected_exchange = st.selectbox("Select Index", ["NS", "BO"], index=0)
            submitted = st.form_submit_button("Add")
            if submitted:
                if ticker_code:
                    if ticker_code not in st.session_state.wishlist:
                        stock = Wishlist_Stock(ticker_code, selected_exchange)
                        st.session_state.wishlist[ticker_code] = {
                            "current_price": stock.last_fetched_price,
                            "exchange": selected_exchange,
                            "BUY": "",
                            "SELL": "",
                            "STATUS": "",
                            "Delete": False
                        }
                        # new_entry = st.session_state.wishlist[ticker_code]
                        st.session_state.wishlist_stock_objects[ticker_code] = stock 
                        # st.session_state.wishlist = pd.concat([st.session_state.wishlist, pd.DataFrame([new_entry])], ignore_index=True) # Store the stock object
                        save_wishlist(st.session_state.wishlist, wishlist_json_path)  # Save changes to JSON
                        st.success(f'Stock {ticker_code} added to the wishlist!')
                    else:
                        st.warning('Stock already in wishlist.')
                else:
                    st.warning('Please enter a ticker code.')

    # --- Editable Table ---
    if mode == "Edit Mode":
        wishlist_df = pd.DataFrame.from_dict(st.session_state.wishlist, orient='index').reset_index()
        wishlist_df.rename(columns={'index': 'Ticker'}, inplace=True)

        edited_df = st.data_editor(
            wishlist_df,
            num_rows="dynamic",
            use_container_width=True,
            key="stock_editor"
        )

        # --- Delete Rows ---
        if st.button("🗑️ Delete Selected Items"):
            edited_df = edited_df[edited_df["Delete"] == False].reset_index(drop=True)
            st.session_state.wishlist = edited_df.set_index("Ticker").to_dict(orient="index")
   
            # st.session_state.wishlist = edited_df
            save_wishlist(st.session_state.wishlist, wishlist_json_path)
            st.rerun()

        # --- Save Button ---
        if st.button("💾 Save Changes"):
            # Fetch latest price and determine status for each stock
            # edited_df["Price"] = edited_df.apply(
            #     lambda row: fetch_price(f"{row['Ticker']}.{row['Index']}"), axis=1
            # )
            edited_df["STATUS"] = edited_df.apply(
                lambda row: set_status(row["current_price"], row["BUY"], row["SELL"]),
                axis=1
            )
            st.session_state.wishlist = edited_df.set_index("Ticker").to_dict(orient="index")
            save_wishlist(st.session_state.wishlist, wishlist_json_path)
            st.success("Watchlist saved and updated with latest prices.")


    # --- Final Display (Current Watchlist with Prices) ---
    if mode == "Normal Mode":
        st.subheader("📊 Current Watchlist")
        df_display = pd.DataFrame.from_dict(st.session_state.wishlist, orient='index').reset_index()

        # Check if data exists in the watchlist
        if not df_display.empty:
            if "Delete" in df_display.columns:
                df_display = df_display.drop(columns=["Delete"])

            # Show the current price along with other details
            st.dataframe(df_display, use_container_width=True)
        else:
            st.warning("No stock data available.")


            