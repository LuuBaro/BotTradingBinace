"""
Test which Gemini models are available in the Google API
"""
import httpx
import asyncio
import json

async def list_gemini_models():
    """List available models"""
    api_key = "AIzaSyCnN-7s9XhMj9rwyaGbKCV9J51uflEm8d0"  # Admin key
    
    # Try listing models from REST API
    print("🔍 Testing Google Generative Language API...")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models",
                params={"key": api_key}
            )
            
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                print(f"✅ Found {len(models)} available models:")
                for model in models:
                    name = model.get("name", "unknown")
                    display_name = model.get("displayName", "")
                    print(f"   - {name} ({display_name})")
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # Try direct generateContent call with different models
    print("\n🔍 Testing generateContent with different models...")
    models_to_test = [
        "gemini-pro",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro-vision",
        "models/gemini-pro",
        "models/gemini-1.5-pro",
        "models/gemini-1.5-flash",
    ]
    
    for model_name in models_to_test:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
                    params={"key": api_key},
                    json={
                        "contents": [{
                            "parts": [{"text": "test"}]
                        }]
                    }
                )
                
                if response.status_code == 200:
                    print(f"   ✅ {model_name}: Works!")
                else:
                    error_msg = response.json().get("error", {}).get("message", "")[:100]
                    print(f"   ❌ {model_name}: {error_msg}")
        except Exception as e:
            print(f"   ❌ {model_name}: {str(e)[:100]}")

asyncio.run(list_gemini_models())
