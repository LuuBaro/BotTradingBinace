import httpx
import asyncio

BASE_URL = "http://localhost:8000/api"

async def test_approval_flow():
    async with httpx.AsyncClient() as client:
        # 1. Login
        print("Logging in...")
        resp = await client.post(f"{BASE_URL}/auth/login", json={"username": "admin", "password": "admin"})
        if resp.status_code != 200:
            print(f"Login failed: {resp.text}")
            return
        
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Login success")

        # 2. Enable Manual Approval Mode
        print("Enabling Manual Approval Mode...")
        resp = await client.post(f"{BASE_URL}/actions/approval-mode?enabled=true", headers=headers)
        print(f"Toggle Response: {resp.json()}")

        # 3. Check status
        resp = await client.get(f"{BASE_URL}/actions/status", headers=headers)
        print(f"Status Response: {resp.json()}")

        print("\nNow wait for worker to generate a decision... (check worker logs)")
        print("Once a decision is 'AWAITING_APPROVAL', we can approve it.")

if __name__ == "__main__":
    asyncio.run(test_approval_flow())
