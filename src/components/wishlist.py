import os
import time
import json
import pandas as pd
import streamlit as st
from classes.wishlist_stock import Wishlist_Stock
from utils.helpers import set_status
import concurrent.futures
import logging
from curl_cffi.requests.exceptions import HTTPError
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
            st.session_state.wishlist_stock_objects = {
                ticker: Wishlist_Stock(
                    ticker_code=ticker,
                    suffix=st.session_state.wishlist[ticker]['exchange'],
                    wishlist_data=st.session_state.wishlist[ticker],
                    requires_fetching=False
                )
                for ticker in st.session_state.wishlist
            }        
        else:
            st.session_state.wishlist_stock_objects = {}
    if 'wishlist_edit_mode' not in st.session_state:
        st.session_state.wishlist_edit_mode = False

    def fetch_and_update_wishlist_stock(ticker_code, stock, buy_threshold, sell_threshold):
        stock.last_fetched_price = stock.get_today_data()
        last_price = stock.last_fetched_price
        status = set_status(last_price, buy_threshold, sell_threshold)
        return ticker_code, last_price, status

    col1, col4, col2, col3 = st.columns([1, 9, 1, 1])

    mode = st.radio("", ["Normal Mode", "Edit Mode"], index=0, horizontal=True)
    
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
                changed_rows = []

                # Gather results and update session state in the main thread
                for future in concurrent.futures.as_completed(futures):
                    ticker_code, last_price, new_status = future.result()
                    current_data = st.session_state.wishlist[ticker_code]
                    old_status = current_data.get("STATUS", "")
                    current_data["Current Price"] = last_price
                    current_data["STATUS"] = new_status

                    if new_status != old_status and new_status in ["BUY", "SELL"]:
                        changed_rows.append({
                            "Stock": ticker_code,
                            "BUY": current_data.get("BUY"),
                            "SELL": current_data.get("SELL"),
                            "STATUS": new_status
                        })
                    logging.info(f"Updated {ticker_code} → Price: {last_price} | Status: {new_status}")

                # Save the updated wishlist to JSON
                save_wishlist(st.session_state.wishlist, wishlist_json_path)

                # Send notifications if any status changed
                if changed_rows:
                    changed_df = pd.DataFrame(changed_rows)
                    send_stock_notifications(changed_df)

            # Display the updated wishlist
            saved_wishlist_df = pd.DataFrame.from_dict(st.session_state.wishlist, orient='index').reset_index()
            saved_wishlist_df = saved_wishlist_df.drop(columns=['exchange', "Delete"])
            saved_wishlist_df.rename(columns={'index': 'Stock'}, inplace=True)
            st.dataframe(saved_wishlist_df, use_container_width=True)

            time.sleep(refresh_interval)  # Pause before next fetch cycle

    if stop_button:
            st.session_state.fetching = False
            print("Stop button has been pressed in wishlist", st.session_state.wishlist_fetching)

    

    if mode == "Edit Mode":
        st.subheader("➕ Add New Stock(s)")
        with st.form("add_stock", clear_on_submit=True):
            ticker_input = st.text_input("Enter Ticker(s) (e.g., RELIANCE, TCS, INFY)")
            selected_exchange = st.selectbox("Select Index", ["NS", "BO"], index=0)
            submitted = st.form_submit_button("Add")

            if submitted:
                if ticker_input:
                    ticker_codes = [ticker.strip().upper() for ticker in ticker_input.split(",") if ticker.strip()]
                    added = []
                    skipped = []
                    invalid = []

                    for ticker_code in ticker_codes:
                        if ticker_code in st.session_state.wishlist:
                            skipped.append(ticker_code)
                            continue

                        try:
                            stock = Wishlist_Stock(ticker_code, selected_exchange, requires_fetching=True)
                            # success, add to wishlist
                            st.session_state.wishlist[ticker_code] = {
                                "Current Price": stock.last_fetched_price,
                                "exchange": selected_exchange,
                                "BUY": "",
                                "SELL": "",
                                "STATUS": "",
                                "Delete": False
                            }
                            st.session_state.wishlist_stock_objects[ticker_code] = stock
                            added.append(ticker_code)
                        except ValueError as e:
                            invalid.append((ticker_code, str(e)))


                    if added:
                        save_wishlist(st.session_state.wishlist, wishlist_json_path)
                        st.success(f"Added: {', '.join(added)}")
                    if skipped:
                        st.warning(f"Already in wishlist: {', '.join(skipped)}")
                    if invalid:
                        for ticker, reason in invalid:
                            st.error(f"❌ {ticker}: {reason}")
                else:
                    st.warning("Please enter at least one ticker code.")


    # --- Editable Table ---
    if mode == "Edit Mode":
        wishlist_df = pd.DataFrame.from_dict(st.session_state.wishlist, orient='index').reset_index()
        wishlist_df.rename(columns={'index': 'Stock'}, inplace=True)

        # Set columns that should be non-editable
        disabled_columns = {"Stock": True, "Current Price": True, "STATUS": True}

        # Data editor for BUY and SELL editing only
        edited_df = st.data_editor(
            wishlist_df,
            use_container_width=True,
            hide_index=False,
            disabled=disabled_columns,
            key="stock_editor"
        )

        col_misc, col_save, col_del = st.columns([8, 1, 1])

        with col_del:
            # --- Delete Rows ---
            if st.button("🗑️ Delete Items"):
                edited_df = edited_df[edited_df["Delete"] == False].reset_index(drop=True)
                st.session_state.wishlist = edited_df.set_index("Stock").to_dict(orient="index")
                save_wishlist(st.session_state.wishlist, wishlist_json_path)
                st.rerun()

        with col_save:
            # --- Save Button ---
            if st.button("💾 Save Changes"):
                # Convert old wishlist to DataFrame for comparison
                old_df = pd.DataFrame.from_dict(st.session_state.wishlist, orient='index').reset_index()
                old_df.rename(columns={'index': 'Stock'}, inplace=True)

                # Recalculate statuses for the edited DataFrame
                edited_df["STATUS"] = edited_df.apply(
                    lambda row: set_status(row["Current Price"], row["BUY"], row["SELL"]),
                    axis=1
                )

                # Identify rows with changed statuses or newly added
                changed_rows = []
                for _, new_row in edited_df.iterrows():
                    old_row = old_df[old_df['Stock'] == new_row['Stock']]
                    if old_row.empty:
                        changed_rows.append(new_row)
                    else:
                        old_status = old_row.iloc[0].get("STATUS", "")
                        if new_row["STATUS"] != old_status:
                            changed_rows.append(new_row)

                # Save updated wishlist to session state and file
                st.session_state.wishlist = edited_df.set_index("Stock").to_dict(orient="index")
                save_wishlist(st.session_state.wishlist, wishlist_json_path)

                # Send notifications for changed rows
                if changed_rows:
                    changed_df = pd.DataFrame(changed_rows)
                    send_stock_notifications(changed_df)

                with col_misc:
                    st.success("Wishlist saved")




    # --- Final Display (Current Watchlist with Prices) ---
    if mode == "Normal Mode":
        st.subheader("📊 Current Wishlist")
        df_display = pd.DataFrame.from_dict(st.session_state.wishlist, orient='index').reset_index()
        df_display.rename(columns={'index': 'Stock'}, inplace=True)

        # Check if data exists in the watchlist
        if not df_display.empty:
            if "Delete" in df_display.columns:
                df_display = df_display.drop(columns=["Delete"])
            if "exchange" in df_display.columns:
                df_display = df_display.drop(columns=["exchange"])

            # Show the current price along with other details
            st.dataframe(df_display, use_container_width=True)
        else:
            st.warning("No stocks added")


            