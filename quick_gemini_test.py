"""
Test Gemini 2.0 Flash - Simple version
"""
import os
import sys

# Thêm project vào path
sys.path.insert(0, 'd:\\BotTradingBinace')

def test_gemini():
    try:
        import httpx
        
        api_key = "AIzaSyC459cP6-fsPC81J6wsWfpytD_5wxcZKt0"
        
        print("\n" + "="*70)
        print("Testing Gemini 2.0 Flash Model")
        print("="*70)
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": "Say 'OK' only"}
                    ]
                }
            ]
        }
        
        response = httpx.post(url, json=payload, timeout=10)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ GEMINI 2.0 FLASH IS WORKING!")
            data = response.json()
            text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            print(f"Response: {text}")
            
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Details: {response.text[:300]}")
        
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}\n")


if __name__ == "__main__":
    test_gemini()
