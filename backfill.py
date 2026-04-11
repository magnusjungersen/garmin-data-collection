"""
One-time backfill script. Collects sleep + HRV data for every day from
START_DATE up to and including yesterday, then writes it all to the
Sleep sheet in one batch.

Usage:
    python backfill.py --start 2024-01-01
"""

import argparse
import time
from datetime import date, timedelta

from collect import (
    TOKEN_STORE,
    SPREADSHEET_ID,
    SHEET_NAME,
    collect_sleep_row,
    get_sheets_client,
)
from garminconnect import Garmin


HEADERS = [
    "date",
    "sleep_start_local",
    "sleep_end_local",
    "total_sleep_seconds",
    "deep_sleep_seconds",
    "light_sleep_seconds",
    "rem_sleep_seconds",
    "awake_seconds",
    "restless_moments",
    "sleep_score",
    "sleep_score_qualifier",
    "sleep_score_feedback",
    "avg_hrv",
    "hrv_status",
    "hrv_weekly_avg",
    "hrv_5min_high",
    "avg_heart_rate",
    "resting_heart_rate",
    "avg_spo2",
    "lowest_spo2",
    "avg_respiration",
    "avg_sleep_stress",
    "body_battery_change",
    "skin_temp_deviation_c",
    "sleep_need_baseline_min",
    "sleep_need_actual_min",
    "breathing_disruption",
]


def date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--start",
        required=True,
        help="Start date in YYYY-MM-DD format",
    )
    args = parser.parse_args()

    start_date = date.fromisoformat(args.start)
    end_date = date.today() - timedelta(days=1)  # up to and including yesterday

    if start_date > end_date:
        print("Start date is in the future, nothing to do.")
        return

    print(f"Backfilling {start_date} → {end_date} ({(end_date - start_date).days + 1} days)\n")

    client = Garmin()
    client.login(TOKEN_STORE)
    print(f"Authenticated as: {client.get_full_name()}\n")

    rows = []
    for target_date in date_range(start_date, end_date):
        try:
            row = collect_sleep_row(client, target_date)
            # Skip days with no sleep data (watch not worn)
            if row["total_sleep_seconds"] is None:
                print(f"  {target_date} — no data, skipping")
            else:
                rows.append(row)
                print(f"  {target_date} — score={row['sleep_score']}, hrv={row['avg_hrv']}, sleep={row['total_sleep_seconds']}s")
        except Exception as e:
            print(f"  {target_date} — error: {e}")

        # Avoid hammering the Garmin API
        time.sleep(0.5)

    print(f"\nCollected {len(rows)} rows with data. Writing to Google Sheets...")

    gc = get_sheets_client()
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

    # Clear the sheet and rewrite from scratch with correct headers
    sheet.clear()
    all_values = [HEADERS] + [[row.get(h, "") for h in HEADERS] for row in rows]
    sheet.update("A1", all_values)

    print(f"Done. {len(rows)} rows written to '{SHEET_NAME}' tab.")


if __name__ == "__main__":
    main()
