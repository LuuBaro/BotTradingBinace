import asyncio
import aiohttp
import json

async def test_audit_trail():
    """Test API với authentication để xem decisions có hiện không"""
    base_url = "http://localhost:8000"
    
    # 1. Login để lấy token
    print("=== Login ===")
    login_data = {
        "username": "admin",
        "password": "admin123"  # Thay bằng password thật
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            # Login
            async with session.post(f"{base_url}/api/auth/login", json=login_data) as response:
                if response.status != 200:
                    # Try form data
                    form = aiohttp.FormData()
                    form.add_field('username', 'admin')
                    form.add_field('password', 'admin123')
                    async with session.post(f"{base_url}/api/auth/login", data=form) as r2:
                        if r2.status != 200:
                            text = await r2.text()
                            print(f"✗ Login failed: {r2.status}")
                            print(f"  Response: {text[:200]}")
                            return
                        login_result = await r2.json()
                else:
                    login_result = await response.json()
                    
            token = login_result.get("access_token")
            if not token:
                print(f"✗ Không lấy được token. Response: {login_result}")
                return
                
            print(f"✓ Login thành công!")
            print(f"  Token: {token[:50]}...")
            
            # 2. Test /decisions endpoint
            print("\n=== Test /decisions endpoint ===")
            headers = {"Authorization": f"Bearer {token}"}
            
            async with session.get(f"{base_url}/api/decisions?limit=10", headers=headers) as response:
                status = response.status
                print(f"Status: {status}")
                
                if status == 200:
                    decisions = await response.json()
                    print(f"✓ Số lượng decisions: {len(decisions)}")
                    
                    if len(decisions) > 0:
                        print(f"\n=== Sample Decision ===")
                        sample = decisions[0]
                        print(json.dumps(sample, indent=2, ensure_ascii=False))
                    else:
                        print("⚠ Không có decisions nào!")
                else:
                    text = await response.text()
                    print(f"✗ Error: {text[:200]}")
            
            # 3. Test /audit endpoint
            print("\n=== Test /audit endpoint ===")
            async with session.get(f"{base_url}/api/audit?limit=10", headers=headers) as response:
                status = response.status
                print(f"Status: {status}")
                
                if status == 200:
                    audit_logs = await response.json()
                    print(f"✓ Số lượng audit logs: {len(audit_logs)}")
                    
                    if len(audit_logs) > 0:
                        print(f"\n=== Sample Audit Log ===")
                        sample = audit_logs[0]
                        print(json.dumps(sample, indent=2, ensure_ascii=False)[:300])
                else:
                    text = await response.text()
                    print(f"✗ Error: {text[:200]}")
                    
        except Exception as e:
            print(f"✗ Lỗi: {str(e)}")
            import traceback
            traceback.print_exc()

asyncio.run(test_audit_trail())
