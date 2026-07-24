# remind_tomorrow.py

import os
from datetime import datetime, timedelta
from send_reminders import run_reminders_for

def main():
    print("📆 Running reminders for appointments tomorrow...")
    run_reminders_for(1, "1-day")

if __name__ == "__main__":
    main()
