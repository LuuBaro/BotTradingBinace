import requests
import json

base_url = "http://localhost:8000/api"

def check_account():
    try:
        # 1. Login
        login_res = requests.post(f"{base_url}/auth/login", json={"username": "admin", "password": "admin"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Get Positions Live
        pos_res = requests.get(f"{base_url}/positions/live", headers=headers)
        if pos_res.status_code == 200:
            data = pos_res.json()
            positions = data.get("positions", [])
            print(f"Live positions found: {len(positions)}")
            for p in positions:
                print(f" - {p['symbol']}: {p['side']} {p['qty']} (PnL: {p['unrealized_pnl']})")
        else:
            print(f"Pos error: {pos_res.text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_account()
