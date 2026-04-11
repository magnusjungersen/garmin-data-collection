"""
Run this after auth_setup.py to print the base64-encoded token for use
as a GitHub Actions secret (GARMIN_TOKENS).

Steps:
1. Copy the printed value
2. Go to your GitHub repo → Settings → Secrets and variables → Actions
3. Create a new secret named GARMIN_TOKENS and paste the value
"""

import base64
import os

token_path = os.path.expanduser("~/.garminconnect/garmin_tokens.json")

if not os.path.exists(token_path):
    print("Token file not found. Run auth_setup.py first.")
    exit(1)

with open(token_path, "rb") as f:
    encoded = base64.b64encode(f.read()).decode()

print("\nCopy the value below and save it as the GitHub secret GARMIN_TOKENS:\n")
print(encoded)
