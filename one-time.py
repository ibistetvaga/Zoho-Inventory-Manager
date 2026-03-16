import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Replace 'YOUR_GRANT_CODE_HERE' with the code from the Zoho Console
GRANT_CODE = 'YOUR_GRANT_CODE_HERE'

url = "https://accounts.zoho.com/oauth/v2/token"

payload = {
    "code": GRANT_CODE,
    "client_id": os.getenv("ZOHO_CLIENT_ID"),
    "client_secret": os.getenv("ZOHO_CLIENT_SECRET"),
    "grant_type": "authorization_code"
}

response = requests.post(url, params=payload)
data = response.json()

if "refresh_token" in data:
    print("Success!")
    print(f"Refresh Token: {data['refresh_token']}")
    print(f"Access Token: {data['access_token']}")
else:
    print("Error:", data)

# Add this line to keep the window open
input("\nCopy your tokens and press Enter to close this window...")