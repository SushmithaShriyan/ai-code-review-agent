"""
Quick test: is our GITHUB_TOKEN actually valid?
Run from backend folder: python test_github_token.py
"""

import httpx
from app.config import settings

headers = {
    "Authorization": f"Bearer {settings.github_token}",
    "Accept": "application/vnd.github+json",
}

resp = httpx.get("https://api.github.com/user", headers=headers)

print(f"Status code: {resp.status_code}")
print(f"Response: {resp.json()}")