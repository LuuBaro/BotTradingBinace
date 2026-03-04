#!/usr/bin/env python3
"""
Debug script to check Binance API key validity and timestamp sync
"""
import asyncio
import time
import hashlib
import hmac
from urllib.parse import urlencode
import aiohttp
from packages.shared.config import settings

async def test_binance_connection():
    print("=" * 80)
    print("🔍 TESTING BINANCE API CONNECTION")
    print("=" * 80)
    
    api_key = settings.binance_api_key
    api_secret = settings.binance_api_secret
    testnet = settings.binance_testnet
    
    print(f"\n📋 Configuration:")
    print(f"   Testnet: {testnet}")
    print(f"   Base URL: {'testnet.binancefuture.com' if testnet else 'fapi.binance.com'}")
    print(f"   API Key: {api_key[:16]}...{'✓' if api_key else '❌'}")
    print(f"   API Secret: {api_secret[:16]}...{'✓' if api_secret else '❌'}")
    
    if not api_key or not api_secret:
        print("\n❌ ERROR: API keys not configured!")
        return
    
    base_url = "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"
    
    # Create session with ThreadedResolver for Windows DNS compatibility
    connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    async with aiohttp.ClientSession(connector=connector) as session:
        # Test 1: Get server time
        print("\n" + "=" * 80)
        print("✅ Test 1: Sync server time")
        print("=" * 80)
        
        try:
            async with session.get(f"{base_url}/fapi/v1/time") as resp:
                data = await resp.json()
                server_time = data.get("serverTime")
                local_time = int(time.time() * 1000)
                offset = server_time - local_time
                
                print(f"   Server Time: {server_time}")
                print(f"   Local Time:  {local_time}")
                print(f"   Offset:      {offset} ms")
                
                if abs(offset) > 1000:
                    print(f"   ⚠️  WARNING: Time offset > 1000ms! This could cause 400 errors!")
                else:
                    print(f"   ✓ Time offset acceptable")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return
        
        # Test 2: Try get account WITHOUT signature (to see if key is valid)
        print("\n" + "=" * 80)
        print("✅ Test 2: Get server time (confirm connection)")
        print("=" * 80)
        
        try:
            headers = {"X-MBX-APIKEY": api_key}
            async with session.get(f"{base_url}/fapi/v1/time", headers=headers) as resp:
                print(f"   Status: {resp.status}")
                if resp.status == 200:
                    print(f"   ✓ Server is reachable with API key")
                else:
                    print(f"   ❌ Issue: Status {resp.status}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return
        
        # Test 3: Try get account WITH signature
        print("\n" + "=" * 80)
        print("✅ Test 3: Get account info (with signature)")
        print("=" * 80)
        
        try:
            # Prepare params
            timestamp = int(time.time() * 1000) + offset
            params = {"timestamp": timestamp}
            
            # Generate signature
            query_string = urlencode(params)
            signature = hmac.new(
                api_secret.encode("utf-8"),
                query_string.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            
            params["signature"] = signature
            
            print(f"   Timestamp: {timestamp}")
            print(f"   Query String: {query_string}")
            print(f"   Signature: {signature}")
            
            headers = {"X-MBX-APIKEY": api_key}
            url = f"{base_url}/fapi/v2/account"
            
            print(f"\n   Making request to: {url}")
            async with session.get(url, params=params, headers=headers) as resp:
                print(f"   Status: {resp.status}")
                
                body = await resp.text()
                print(f"   Response: {body[:200]}")
                
                if resp.status == 200:
                    print(f"   ✅ SUCCESS! Account data retrieved")
                    data = await resp.json()
                    # Don't print actual data - just confirm
                    print(f"   Keys in response: {list(data.keys())[:5]}")
                elif resp.status == 400:
                    print(f"   ❌ ERROR 400: Bad Request")
                    print(f"   Response: {body}")
                    
                    # Try to diagnose
                    if "Invalid" in body:
                        print(f"\n   🔍 Diagnostics:")
                        print(f"      - API key might be invalid/expired")
                        print(f"      - API secret might be incorrect")
                        print(f"      - Signature calculation might be wrong")
                    if "Timestamp" in body:
                        print(f"\n   🔍 Diagnostics:")
                        print(f"      - Server time drift issue")
                        print(f"      - Try adjusting system clock")
                else:
                    print(f"   ❌ ERROR {resp.status}")
                    print(f"   Response: {body}")
        
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 4: Check if API key has required permissions
        print("\n" + "=" * 80)
        print("✅ Test 4: Check API key status")
        print("=" * 80)
        
        try:
            # This endpoint doesn't require signature
            async with session.get(
                f"{base_url}/fapi/v1/apiKeyInfo",
                headers={"X-MBX-APIKEY": api_key}
            ) as resp:
                print(f"   Status: {resp.status}")
                if resp.status == 200:
                    print(f"   ✓ Valid API key")
                elif resp.status == 401:
                    print(f"   ❌ Unauthorized - API key is invalid or disabled")
                else:
                    print(f"   ❌ Status {resp.status}")
        except Exception as e:
            print(f"   ⚠️  Cannot check (may require signed request): {e}")
    
    print("\n" + "=" * 80)
    print("📝 RECOMMENDATIONS:")
    print("=" * 80)
    print("""
1. If you see "Timestamp" in error:
   → System time is out of sync with Binance's servers
   → Run: ntpdate -u pool.ntp.org  (Linux/Mac)
   → Or: w32tm /resync  (Windows)

2. If you see "Invalid" or "Unauthorized":
   → Check if API key is correct
   → Check if API secret is correct
   → Check if API key is enabled on Binance dashboard
   → Check if testnet checkbox matches your key type

3. If offset is > 1000ms:
   → Adjust system clock before running bot

4. To regenerate API key:
   → Go to https://testnet.binancefuture.com
   → Account Settings → API Management
   → Create new key with all permissions enabled
   → Update .env file
    """)

if __name__ == "__main__":
    asyncio.run(test_binance_connection())
