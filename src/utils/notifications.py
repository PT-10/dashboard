import os
import platform
from plyer import notification

def send_stock_notifications(df):
    os_type = platform.system().lower()  # OS type initialization outside the loop
    
    alert_messages = []  # List to collect the alert messages
    
    for idx, row in df.iterrows():
        try:
            ticker = row["Stock"]
            buy_price = row["BUY"]
            sell_price = row["SELL"]
            current_price = row["Present Value"]
            status = row["STATUS"]  # The status of the stock

            # Generate alert messages based on thresholds and status
            if status == "SELL":
                alert_messages.append(f"📈 {ticker}: SELL ALERT! (Above {sell_price})")
            elif status == "BUY":
                alert_messages.append(f"📉 {ticker}: BUY ALERT! (Below {buy_price})")
            # elif status == "":
            #     alert_messages.append(f"✅ {ticker}: HOLD (Within Range)")
            # else:
            #     # Handle case where status is not recognized or empty
            #     alert_messages.append(f"⚠️ {ticker}: Unknown status '{status}' for price {current_price:.2f}")
        except Exception as e:
            alert_messages.append(f"⚠️ Error fetching data for {row['Stock']}: {str(e)}")

    # Send notification if there are any alert messages
    if alert_messages:
        message = "\n".join(alert_messages)  # Combine all alerts into one message
        send_notification(os_type, "Stock Price Summary", message)

def send_notification(os_type, title, message):
    """Send a notification based on the operating system."""
    if os_type == "windows":
        send_windows_notification(title, message)
    elif os_type == "linux":
        send_linux_notification(title, message)

def send_windows_notification(title, message):
    """Send a notification on Windows using plyer."""
    notification.notify(
        title=title,
        message=message,
        app_name="Stock Price Alert",
        timeout=10  # Duration in seconds
    )

def send_linux_notification(title, message):
    """Send a notification on Linux using notify-send."""
    os.system(f'notify-send "{title}" "{message}"')
