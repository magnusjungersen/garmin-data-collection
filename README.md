# Garmin Data Collection

Automatically collects daily sleep and health data from Garmin Connect, syncs it to Google Sheets, and publishes an interactive sleep consistency chart to GitHub Pages — ready to embed in Notion or any iframe-capable tool.

**Live chart:** `https://<your-username>.github.io/<your-repo>/sleep_consistency.html`

---

## What it does

- Runs daily via GitHub Actions (8 AM CET / 9 AM CEST)
- Collects sleep + HRV data for yesterday and today from Garmin Connect
- Writes/updates rows in a Google Sheet (usable as a Looker Studio data source)
- Regenerates an interactive Plotly chart and publishes it to GitHub Pages

---

## Architecture

```
GitHub Actions (daily, 7 AM UTC)
    │
    ├── collect.py          → Garmin Connect API → Google Sheets (Sleep tab)
    │
    └── garmin_sleep_consistency.py
            │
            └── garmin_data.py  ← reads from Google Sheets
                    │
                    └── docs/sleep_consistency.html → GitHub Pages
```

The Garmin API is called **once per day** by `collect.py`. All plotting scripts read from Google Sheets so there are no redundant API calls.

---

## Prerequisites

- Python 3.12+
- A Garmin Connect account with a compatible device (tested on Venu 3)
- A Google account
- A GitHub account with GitHub Pages enabled on your repo

---

## Setup guide

### 1. Clone and install

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Authenticate with Garmin Connect

Run the interactive auth script once locally. This creates a token file at `~/.garminconnect/garmin_tokens.json` that auto-refreshes indefinitely.

```bash
python auth_setup.py
```

You will be prompted for your Garmin email, password, and MFA code (if enabled). If Garmin requires MFA, complete it — subsequent runs will use the saved token without prompting.

### 3. Export the token for GitHub Actions

```bash
python export_token.py
```

Copy the printed base64 string — you'll need it in step 6.

### 4. Set up Google Sheets

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a new project
2. Enable the **Google Sheets API** for the project
3. Go to **IAM & Admin → Service Accounts → Create service account** (no roles needed)
4. On the service account page: **Keys → Add Key → Create new key → JSON** — download the file and save it as `credentials.json` in the project root (it is gitignored)
5. Create a Google Sheet and add a tab named exactly `Sleep`
6. Share the sheet with the service account email (e.g. `name@project.iam.gserviceaccount.com`) — give it **Editor** access
7. Copy the spreadsheet ID from the URL: `docs.google.com/spreadsheets/d/`**`SPREADSHEET_ID`**`/edit`

### 5. Backfill historical data

Run this once to populate your sheet with all past data from a given start date:

```bash
python backfill.py --start 2024-01-01
```

Skips days with no recorded sleep (watch not worn). Safe to re-run — it clears and rewrites the sheet from scratch.

### 6. Add GitHub Actions secrets

Go to your GitHub repo → **Settings → Secrets and variables → Actions** and create:

| Secret | Value |
|---|---|
| `GARMIN_TOKENS` | output of `python export_token.py` |
| `GARMIN_EMAIL` | your Garmin account email |
| `GARMIN_PASSWORD` | your Garmin account password |
| `GOOGLE_CREDENTIALS_JSON` | full contents of `credentials.json` |
| `SPREADSHEET_ID` | your Google Sheet ID |

`GARMIN_EMAIL` and `GARMIN_PASSWORD` are stored as a fallback for re-authentication if the token is ever invalidated (e.g. after a password change).

### 7. Enable GitHub Pages

Go to your repo → **Settings → Pages → Source: Deploy from a branch** → Branch: `main`, folder: `/docs`.

The chart will be live at:
```
https://<your-username>.github.io/<your-repo>/sleep_consistency.html
```

### 8. Test the workflow

Trigger a manual run from **Actions → Garmin Data Sync → Run workflow** and verify both steps complete successfully.

---

## Project structure

```
.
├── auth_setup.py                  # One-time local Garmin authentication
├── export_token.py                # Exports saved token as base64 for GitHub secret
├── collect.py                     # Daily sync: Garmin → Google Sheets
├── backfill.py                    # One-time historical import
├── garmin_data.py                 # Shared data layer — reads from Google Sheets
├── garmin_sleep_consistency.py    # Generates sleep window chart → docs/
├── docs/
│   ├── index.html                 # Redirects to sleep_consistency.html
│   └── sleep_consistency.html    # Published chart (GitHub Pages)
├── requirements.txt
├── .gitignore                     # Excludes credentials.json, .venv, *.json
└── .github/
    └── workflows/
        └── garmin-sync.yml        # Daily GitHub Actions workflow
```

---

## Data collected (Google Sheets — Sleep tab)

| Column | Description |
|---|---|
| `date` | Calendar date (local timezone, Europe/Amsterdam) |
| `sleep_start_local` | Bedtime in local time |
| `sleep_end_local` | Wake time in local time |
| `total_sleep_seconds` | Total sleep duration |
| `deep/light/rem/awake_seconds` | Sleep stage breakdown |
| `restless_moments` | Number of restless moments |
| `sleep_score` | Garmin overall sleep score (0–100) |
| `sleep_score_qualifier` | EXCELLENT / GOOD / FAIR / POOR |
| `sleep_score_feedback` | Garmin's feedback key |
| `avg_hrv` | Overnight average HRV |
| `hrv_status` | BALANCED / UNBALANCED / etc. |
| `hrv_weekly_avg` | 7-day rolling HRV average |
| `hrv_5min_high` | Best 5-minute HRV of the night |
| `avg/resting_heart_rate` | Sleep and resting heart rate |
| `avg_spo2` / `lowest_spo2` | Blood oxygen saturation |
| `avg_respiration` | Breathing rate during sleep |
| `avg_sleep_stress` | Stress level during sleep |
| `body_battery_change` | Body battery gained overnight |
| `skin_temp_deviation_c` | Skin temperature deviation from baseline |
| `sleep_need_baseline/actual_min` | Garmin's sleep need recommendation |
| `breathing_disruption` | Breathing disruption severity |

---

## Adding new plots

`garmin_data.py` is the shared data layer. To add a new visualisation:

1. Add a new `fetch_*` function to `garmin_data.py` if you need a different data shape
2. Create a new `garmin_<chart_name>.py` that imports from `garmin_data` and writes to `docs/<chart_name>.html`
3. Add a step to `.github/workflows/garmin-sync.yml` after the existing **Generate charts** step:
   ```yaml
   - name: Generate <chart name>
     run: python garmin_<chart_name>.py
     env:
       GOOGLE_CREDENTIALS_JSON: ${{ secrets.GOOGLE_CREDENTIALS_JSON }}
       SPREADSHEET_ID: ${{ secrets.SPREADSHEET_ID }}
   ```
4. Link to it from `docs/index.html`

---

## Timezone

All dates and times are stored in **Europe/Amsterdam** (CET/CEST). The timezone offset (UTC+1 in winter, UTC+2 in summer) is handled automatically by Python's `zoneinfo` module — DST transitions require no manual intervention.

If you are in a different timezone, update `LOCAL_TZ` in [garmin_data.py](garmin_data.py) and [collect.py](collect.py).

---

## Token maintenance

Garmin tokens auto-refresh indefinitely as long as they remain valid. If a token is ever invalidated (password change, Garmin session revocation), re-run locally:

```bash
python auth_setup.py
python export_token.py
```

Then update the `GARMIN_TOKENS` secret in GitHub.

---

## Security notes

- `credentials.json` is gitignored — never commit it
- All secrets are stored in GitHub Actions secrets, never in code
- The Google service account only has access to the specific sheet you share with it
- Consider rotating the service account key periodically in Google Cloud Console
