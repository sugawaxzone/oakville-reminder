import os
import requests
import pytz
from datetime import datetime, timedelta
from dateutil import parser
from collections import defaultdict

# ENV VARS
ZENOTI_API_KEY = os.getenv("ZENOTI_API_KEY")
ZENOTI_ORG_ID = os.getenv("ZENOTI_ORG_ID")
ZENOTI_CENTER_ID = os.getenv("ZENOTI_CENTER_ID")
OPENPHONE_API_KEY = os.getenv("OPENPHONE_API_KEY")
OPENPHONE_NUMBER_ID = os.getenv("OPENPHONE_NUMBER_ID")
TEST_MODE = os.getenv("TEST_MODE", "false").lower()  # Default to test mode

def get_unconfirmed_appointments(target_date, label=""):
    est = pytz.timezone("America/Toronto")

    if target_date.tzinfo is None:
        target_date = target_date.replace(tzinfo=pytz.utc).astimezone(est)
    else:
        target_date = target_date.astimezone(est)

    start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    end_date = target_date.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()

    print(f"\n📅 [{label}] Checking appointments from {start_date} to {end_date} (EST)")
    url = f"https://api.zenoti.com/v1/appointments?start_date={start_date}&end_date={end_date}&center_id={ZENOTI_CENTER_ID}&include_service_details=true"
    print(f"🔗 [{label}] API URL: {url}")

    headers = {
        "Authorization": f"apikey {ZENOTI_API_KEY}",
        "org": ZENOTI_ORG_ID
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ [{label}] Failed to fetch appointments: {e}")
        return []

    appointments = response.json()
    print(f"🔍 [{label}] Total appointments received: {len(appointments)}")

    guests = defaultdict(list)

    for appt in appointments:
        guest = appt.get("guest") or {}
        name = guest.get("first_name", "Guest")

        raw_phone = guest.get("mobile") or guest.get("phone_number") or guest.get("phone")
        if isinstance(raw_phone, dict):
            phone = raw_phone.get("display_number", "") or ""
        elif isinstance(raw_phone, str):
            phone = raw_phone
        else:
            phone = ""

        phone = phone.strip()
        phone = ''.join(filter(str.isdigit, phone))
        if not phone:
            print(f"⚠️ [{label}] Skipping {name} — No valid phone number.")
            continue

        phone = f"+{phone}" if not phone.startswith("+") else phone
        

        status = appt.get("status", None)
        start_time_str = appt.get("start_time", "")
        if not start_time_str or status != 0:
            continue

        try:
            start_time = parser.parse(start_time_str)
        except:
            print(f"⚠️ [{label}] Invalid start time for {name}. Skipping.")
            continue

        guests[phone].append({
            "name": name,
            "start": start_time
        })

    unique_appointments = []

    for phone, entries in guests.items():
        earliest = min(entries, key=lambda x: x["start"])
        unique_appointments.append({
            "name": earliest["name"],
            "phone": phone,
            "date": earliest["start"].isoformat()
        })

    print(f"✅ [{label}] Found {len(unique_appointments)} unconfirmed appointments.")
    return unique_appointments

def send_sms(to, message):
    url = "https://api.openphone.com/v1/messages"
    headers = {
        "Authorization": OPENPHONE_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "from": OPENPHONE_NUMBER_ID,
        "to": [to],
        "content": message
    }

    print(f"📤 Sending SMS to {to}...\nPayload: {payload}")

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 202:
            print(f"❌ Failed to send SMS | Status: {response.status_code}")
            print(response.text)
        else:
            print("✅ SMS sent successfully.")
    except requests.exceptions.RequestException as e:
        print(f"❌ OpenPhone request error for {to}: {e}")

def run_reminders_for(days_ahead, label):
    est = pytz.timezone("America/Toronto")
    now = datetime.now(est)
    target_date = now + timedelta(days=days_ahead)

    print(f"\n📆 [{label}] Running reminder for appointments on: {target_date.strftime('%Y-%m-%d')}")

    appointments = get_unconfirmed_appointments(target_date, label)
    if not appointments:
        print(f"✅ [{label}] No unconfirmed appointments found.")
        return

    print(f"📭 [{label}] Sending reminders to {len(appointments)} clients...\n")

    for appt in appointments:
        name = appt["name"]
        phone = appt["phone"]

        try:
            start = parser.parse(appt["date"])
            day_str = start.strftime("%A")
            date_str = start.strftime("%B %d")
            time_str = start.strftime("%I:%M %p")

            message = (
                f"Hello {name}, your appointment at SugaWax Zone is scheduled for {day_str}, {date_str} at {time_str}. Please reply to confirm or make changes."
            )

            if TEST_MODE == "true":
                print(f"[TEST MODE - {label}] Would send SMS to {phone}: {message}")
            else:
                send_sms(phone, message)

        except Exception as e:
            print(f"❌ [{label}] Error processing appointment for {name} ({phone}): {e}")
            continue

def main():
    try:
        run_reminders_for(2, "2-day")
    except Exception as e:
        print(f"⚠️ [2-day] Flow error: {e}")

    try:
        run_reminders_for(1, "1-day")
    except Exception as e:
        print(f"⚠️ [1-day] Flow error: {e}")

if __name__ == "__main__":
    main()
