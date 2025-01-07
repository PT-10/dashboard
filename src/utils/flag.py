import os
import datetime

# Define the path to store the date of the last execution
flag_file = "./data/last_execution_date.txt"

def has_run_today():
    """Check if the function has already run today."""
    if not os.path.exists(flag_file):
        return False
    
    with open(flag_file, 'r') as f:
        last_run_date = f.read().strip()
    
    today = datetime.date.today().strftime('%Y-%m-%d')
    
    return last_run_date == today

def mark_run_today():
    """Mark the function as run today."""
    today = datetime.date.today().strftime('%Y-%m-%d')
    with open(flag_file, 'w') as f:
        f.write(today)
