# remind_in_2_days.py

import os
from datetime import datetime, timedelta
from send_reminders import run_reminders_for

def main():
    print("📆 Running reminders for appointments 2 days from today...")
    run_reminders_for(2, "2-day")

if __name__ == "__main__":
    main()
