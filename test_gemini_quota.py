"""
Test Gemini API Key Quota & Status
"""
import asyncio
import httpx
import json


async def test_gemini_quota():
    """Test Gemini API key"""
    
    api_key = "AIzaSyC459cP6-fsPC81J6wsWfpytD_5wxcZKt0"
    
    print("="*70)
    print("🔑 Gemini API Key Status Check")
    print("="*70)
    print(f"\n✅ API Key: {api_key[:20]}...{api_key[-10:]}")
    
    # Test with simple prompt
    print("\n📋 Testing Gemini API with simple request...")
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": "Say 'Gemini API works!'"
                            }
                        ]
                    }
                ]
            }
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"\n   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ API CALL SUCCESSFUL!")
                result = response.json()
                if 'candidates' in result:
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    print(f"   Response: {content}")
                    print("\n   ✅ GEMINI API IS WORKING WITH QUOTA!")
                else:
                    print(f"   Response: {result}")
                    
            elif response.status_code == 400:
                error = response.json()
                print(f"   ❌ BAD REQUEST")
                print(f"   Error: {error.get('error', {}).get('message', 'Unknown error')}")
                
            elif response.status_code == 401:
                print("   ❌ AUTHENTICATION FAILED")
                error = response.json()
                print(f"   Error: {error.get('error', {}).get('message', 'Invalid API Key')}")
                
            elif response.status_code == 429:
                print("   ⚠️  RATE LIMITED - Too many requests")
                error = response.json()
                print(f"   Error: {error.get('error', {}).get('message', 'Rate limited')}")
                
            elif response.status_code == 403:
                print("   ❌ QUOTA EXCEEDED or ACCESS DENIED")
                error = response.json()
                print(f"   Error: {error.get('error', {}).get('message', 'Quota exceeded')}")
                
            else:
                print(f"   ❌ Error {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    print("\n" + "="*70)


asyncio.run(test_gemini_quota())
