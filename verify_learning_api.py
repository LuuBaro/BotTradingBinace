import httpx
import json

base_url = "http://localhost:8000/api"

def test_endpoint():
    print(f"Testing GET {base_url}/learning/trader-context/history...")
    try:
        r = httpx.get(f"{base_url}/learning/trader-context/history")
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")
    except Exception as e:
        print(f"Error: {e}")

    print(f"\nTesting POST {base_url}/learning/import-trader-context...")
    try:
        payload = {"trader_prompt": "Test instruction", "trader_name": "Antigravity Test"}
        r = httpx.post(f"{base_url}/learning/import-trader-context", json=payload)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_endpoint()
