"""
List Available Gemini Models
"""
import asyncio
import httpx


async def list_gemini_models():
    """List all available Gemini models"""
    
    api_key = "AIzaSyC459cP6-fsPC81J6wsWfpytD_5wxcZKt0"
    
    print("="*70)
    print("🔍 Listing Available Gemini Models")
    print("="*70)
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            
            response = await client.get(url)
            
            if response.status_code == 200:
                result = response.json()
                models = result.get('models', [])
                
                print(f"\n✅ Found {len(models)} models:")
                for model in models[:10]:
                    model_name = model.get('name', 'unknown')
                    print(f"   • {model_name}")
                    
            else:
                print(f"❌ Error {response.status_code}")
                print(f"Response: {response.text[:300]}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "="*70)


asyncio.run(list_gemini_models())
