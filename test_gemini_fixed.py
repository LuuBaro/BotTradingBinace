"""
Test Gemini 2.0 Flash API with actual chat completion
"""
import asyncio
import httpx


async def test_gemini_chat():
    """Test Gemini API with correct model"""
    
    api_key = "AIzaSyC459cP6-fsPC81J6wsWfpytD_5wxcZKt0"
    
    print("="*70)
    print("🧪 Testing Gemini 2.0 Flash Chat Completion")
    print("="*70)
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": "Hello, can you respond with 'OK'?"
                            }
                        ]
                    }
                ]
            }
            
            response = await client.post(url, json=payload)
            
            print(f"\n🔗 URL: {url[:70]}...")
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ SUCCESS! Model is working!")
                print(f"Response: {result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')[:100]}")
                
            else:
                print(f"❌ Error {response.status_code}")
                print(f"Response: {response.text[:500]}")
                
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print("="*70)


asyncio.run(test_gemini_chat())
