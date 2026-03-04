"""
Check OpenAI API Key Status & Quota
Kiểm tra xem API key mới có quota không
"""
import asyncio
import httpx
import os
from packages.shared.config import settings


async def check_openai_quota():
    """Check OpenAI API key status and quota"""
    
    api_key = settings.openai_api_key
    
    if not api_key:
        print("❌ OpenAI API Key not found in .env!")
        return
    
    print("="*70)
    print("🔑 OpenAI API Key Status Check")
    print("="*70)
    print(f"\n✅ API Key Found:")
    print(f"   Preview: {api_key[:20]}...{api_key[-10:]}")
    
    # Test 1: Check models endpoint
    print("\n📋 Test 1: Checking available models...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "BotTrading/1.0"
                }
            )
            
            if response.status_code == 200:
                print("   ✅ API Key is VALID!")
                models = response.json()
                model_list = [m['id'] for m in models.get('data', [])[:5]]
                print(f"   ✅ Available models: {', '.join(model_list)}")
            elif response.status_code == 401:
                print("   ❌ AUTHENTICATION FAILED - Invalid API Key")
                print(f"   Error: {response.text}")
            elif response.status_code == 429:
                print("   ⚠️  RATE LIMITED - Too many requests")
            else:
                print(f"   ❌ Error {response.status_code}: {response.text}")
                
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
    
    # Test 2: Try a simple completion
    print("\n📋 Test 2: Testing with simple API call...")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": "Say 'API works!'"}
                ],
                "max_tokens": 10,
                "temperature": 0.7
            }
            
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                print("   ✅ API CALL SUCCESSFUL!")
                result = response.json()
                print(f"   Message: {result['choices'][0]['message']['content']}")
                print(f"   Tokens used: {result['usage']['total_tokens']}")
            elif response.status_code == 401:
                print("   ❌ INVALID API KEY")
            elif response.status_code == 429:
                print("   ⚠️  QUOTA EXCEEDED - No tokens left!")
                print(f"   Error: {response.json().get('error', {}).get('message', 'Unknown error')}")
            elif response.status_code == 403:
                print("   ❌ ACCESS DENIED - Check organization or billing")
                print(f"   Error: {response.json().get('error', {}).get('message', 'Unknown error')}")
            else:
                print(f"   ❌ Error {response.status_code}")
                print(f"   {response.text}")
                
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        
    print("\n" + "="*70)


asyncio.run(check_openai_quota())
