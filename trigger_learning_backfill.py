#!/usr/bin/env python3
"""Trigger backfill by accessing learning endpoint"""
import requests
import json

BASE_URL = "http://localhost:8000/api"

# Login as admin (who can view all users' data)
login_res = requests.post(f"{BASE_URL}/auth/login", json={"username": "admin", "password": "admin"})
if login_res.status_code != 200:
    print(f"❌ Login failed: {login_res.text}")
    exit(1)

token = login_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Get learning dashboard metrics for trader user (this should trigger backfill)
print("🔄 Calling /api/learning/dashboard-metrics for trader user...")
res = requests.get(f"{BASE_URL}/learning/dashboard-metrics?user_id=bfb06bb5-5695-4eb5-ae13-8975762e4394", headers=headers)

print(f"\n📊 Response Status: {res.status_code}")
print(f"📄 Response:\n{json.dumps(res.json(), indent=2)}")

if res.status_code == 200:
    data = res.json()
    if data.get("status") == "success":
        print("\n✅ Learning page should now show trade analysis!")
    elif data.get("status") == "insufficient_data":
        trades = data.get("trades_recorded", 0)
        needed = data.get("needed_for_analysis", 5)
        print(f"\n⚠️  Still insufficient data: {trades}/{needed} trades")
        print("     (Backfill may not have executed)")
