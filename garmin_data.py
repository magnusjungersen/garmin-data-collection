"""
Shared data layer for plotting scripts.
Reads from Google Sheets (populated daily by collect.py) so the Garmin API
is only called once per day. Import this in any plotting script.
"""

import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import gspread
from google.oauth2.service_account import Credentials

LOCAL_TZ = ZoneInfo("Europe/Amsterdam")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1kw91StScRpDGMtyTvgO5GCQHX43I28llMQ0b78EUf2E")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def get_sheets_client() -> gspread.Client:
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    return gspread.authorize(creds)


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=LOCAL_TZ)


def _int(value: str) -> int | None:
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _float(value: str) -> float | None:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def fetch_sleep_data(days: int = 30) -> list[dict]:
    """
    Read the last `days` days of sleep data from the Sleep sheet.
    Returns a list of dicts, oldest first, skipping days with no sleep recorded.
    """
    gc = get_sheets_client()
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet("Sleep")
    records = sheet.get_all_records()

    rows = []
    for r in records:
        sleep_start = _parse_dt(r.get("sleep_start_local", ""))
        sleep_end = _parse_dt(r.get("sleep_end_local", ""))
        total = _int(r.get("total_sleep_seconds"))

        if not sleep_start or not sleep_end or not total:
            continue

        rows.append({
            "date": datetime.strptime(r["date"], "%Y-%m-%d").date(),
            "sleep_start": sleep_start,
            "sleep_end": sleep_end,
            "total_sleep_seconds": total,
            "deep_sleep_seconds": _int(r.get("deep_sleep_seconds")),
            "light_sleep_seconds": _int(r.get("light_sleep_seconds")),
            "rem_sleep_seconds": _int(r.get("rem_sleep_seconds")),
            "awake_seconds": _int(r.get("awake_seconds")),
            "sleep_score": _int(r.get("sleep_score")),
            "avg_hrv": _float(r.get("avg_hrv")),
        })

    # Sort and limit to requested window
    rows.sort(key=lambda r: r["date"])
    return rows[-days:]
