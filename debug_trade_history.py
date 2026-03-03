#!/usr/bin/env python3
"""Check what the Trade History API endpoint is returning"""
import requests

BASE_URL = "http://localhost:8000/api"

# Login as admin
login_res = requests.post(f"{BASE_URL}/auth/login", json={"username": "admin", "password": "admin"})
if login_res.status_code != 200:
    print(f"Login failed: {login_res.text}")
    exit(1)

token = login_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Get Trade History
res = requests.get(f"{BASE_URL}/trades/history", headers=headers)
print(f"Status: {res.status_code}")
print(f"Response: {res.json()}")
