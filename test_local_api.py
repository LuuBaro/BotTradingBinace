import requests
import json

base_url = "http://localhost:8000/api"
login_payload = {"username": "admin", "password": "admin_password"} # Assuming these are defaults or I'll check user_manager

def test_api():
    try:
        # 1. Login
        login_res = requests.post(f"{base_url}/auth/login", json={"username": "admin", "password": "admin"})
        if login_res.status_code != 200:
            print(f"Login failed: {login_res.text}")
            return
        
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Get Trades
        trades_res = requests.get(f"{base_url}/trades", headers=headers)
        print(f"Trades status: {trades_res.status_code}")
        if trades_res.status_code == 200:
            trades = trades_res.json()
            print(f"Found {len(trades)} trades")
        
        # 3. Get Balance
        balance_res = requests.get(f"{base_url}/wallet/balance", headers=headers)
        print(f"Balance status: {balance_res.status_code}")
        if balance_res.status_code == 200:
            print(f"Balance data: {balance_res.json()}")
        else:
            print(f"Balance error: {balance_res.text}")
            
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_api()
