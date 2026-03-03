import asyncio
import aiohttp
import json

async def test_decisions_api():
    """Test API endpoint để lấy decisions"""
    base_url = "http://localhost:8000"
    
    # Test endpoints
    endpoints = [
        "/api/decisions",
        "/api/decisions/list",
        "/api/audit/decisions",
        "/api/audit-trail",
        "/api/trace"
    ]
    
    async with aiohttp.ClientSession() as session:
        print("\n=== Kiểm tra API Endpoints ===\n")
        
        for endpoint in endpoints:
            try:
                async with session.get(f"{base_url}{endpoint}") as response:
                    status = response.status
                    if status == 200:
                        data = await response.json()
                        print(f"✓ {endpoint}")
                        print(f"  Status: {status}")
                        if isinstance(data, list):
                            print(f"  Records: {len(data)}")
                            if len(data) > 0:
                                print(f"  Sample: {json.dumps(data[0], indent=2, ensure_ascii=False)[:200]}...")
                        elif isinstance(data, dict):
                            print(f"  Keys: {list(data.keys())}")
                        print()
                    else:
                        print(f"✗ {endpoint}")
                        print(f"  Status: {status}")
                        text = await response.text()
                        print(f"  Error: {text[:100]}")
                        print()
            except Exception as e:
                print(f"✗ {endpoint}")
                print(f"  Error: {str(e)}")
                print()

asyncio.run(test_decisions_api())
