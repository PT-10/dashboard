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
        # message = "\n".join(alert_messages)  # Combine all alerts into one message
        send_notification(os_type, "Stock Price Summary", alert_messages)

def send_notification(os_type, title, alert_messages):
    """Send a notification based on the operating system."""
    if os_type == "windows":
        send_windows_notification(title, alert_messages)
    elif os_type == "linux":
        message = "\n".join(alert_messages)
        send_linux_notification(title, message)

def send_windows_notification(title, message):
    """
    Send a notification on Windows using plyer, ensuring each chunk is within the limit.
    The message is split into chunks if it's too long to fit in a single notification.
    """
    max_message_length = 256  # Define the maximum length for each message chunk
    current_chunk = ""  # Initialize an empty string for the current chunk
    chunks = []  # List to store the chunks of the message

    # Split the message into chunks
    for alert_message in message:
        # Check if adding this message to the current chunk exceeds the length limit
        if len(current_chunk) + len(alert_message) + 1 > max_message_length:  # +1 for newline separator
            # If it does, push the current chunk and start a new one with the current message
            chunks.append(current_chunk)
            current_chunk = alert_message
        else:
            # Otherwise, add the message to the current chunk
            if current_chunk:
                current_chunk += "\n" + alert_message  # Add a newline before appending
            else:
                current_chunk = alert_message  # Start the chunk with the current message

    # Add the last chunk if there's any remaining
    if current_chunk:
        chunks.append(current_chunk)

    # Send each chunk as a separate notification
    for chunk in chunks:
        notification.notify(
            title=title,
            message=chunk,
            app_name="Stock Price Alert",
            timeout=30  # Duration in seconds
        )

def send_linux_notification(title, message):
    """Send a notification on Linux using notify-send."""
    os.system(f'notify-send "{title}" "{message}"')
