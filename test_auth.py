"""
Quick sanity check — confirms the saved token can authenticate
and reach the Garmin Connect API.
"""

import os
from garminconnect import Garmin

TOKEN_STORE = os.path.expanduser("~/.garminconnect")

client = Garmin()
client.login(TOKEN_STORE)

import json
from datetime import date, timedelta

info = client.get_full_name()
print(f"Authenticated as: {info}\n")

yesterday = (date.today() - timedelta(days=1)).isoformat()

def summarize(data, max_list_items=2):
    """Recursively print structure, truncating long lists."""
    if isinstance(data, dict):
        return {k: summarize(v, max_list_items) for k, v in data.items()}
    if isinstance(data, list):
        truncated = [summarize(i, max_list_items) for i in data[:max_list_items]]
        if len(data) > max_list_items:
            truncated.append(f"... ({len(data) - max_list_items} more items)")
        return truncated
    return data

print(f"--- SLEEP DATA ({yesterday}) ---")
sleep = client.get_sleep_data(yesterday)
print(json.dumps(summarize(sleep), indent=2))

print(f"\n--- HRV DATA ({yesterday}) ---")
hrv = client.get_hrv_data(yesterday)
print(json.dumps(summarize(hrv), indent=2))
