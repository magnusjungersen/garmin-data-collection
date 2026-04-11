"""
Run this script once locally to authenticate with Garmin Connect.
It will prompt for your email, password, and MFA code (if enabled).
Tokens are saved to ~/.garminconnect/garmin_tokens.json and auto-refresh
indefinitely in subsequent runs.

After running this, use export_token.py to get the token for GitHub Actions.
"""

import os
from garminconnect import Garmin

TOKEN_STORE = os.path.expanduser("~/.garminconnect")

email = input("Garmin email: ")
password = input("Garmin password: ")

client = Garmin(
    email=email,
    password=password,
    prompt_mfa=lambda: input("MFA code (leave blank if not enabled): ") or None,
)

client.login(TOKEN_STORE)

print(f"\nAuthentication successful. Tokens saved to {TOKEN_STORE}/garmin_tokens.json")
print("Run export_token.py to get the token string for GitHub Actions.")
