#!/usr/bin/env python3
"""
Debug Binance signature calculation step by step
"""
import hashlib
import hmac
import time
from urllib.parse import urlencode
from packages.shared.config import settings

def test_signature():
    print("=" * 80)
    print("🔍 DEBUG: BINANCE SIGNATURE CALCULATION")
    print("=" * 80)
    
    api_key = settings.binance_api_key
    api_secret = settings.binance_api_secret
    
    print(f"\n📋 Credentials (first 20 chars):")
    print(f"   API Key:    {api_key[:20]}...")
    print(f"   API Secret: {api_secret[:20]}...")
    
    # Step 1: Prepare params
    timestamp = int(time.time() * 1000) + settings.binance_timestamp_offset
    params = {"timestamp": timestamp}
    
    print(f"\n📝 Step 1: Prepare params")
    print(f"   Timestamp: {timestamp}")
    print(f"   Params: {params}")
    
    # Step 2: Create query string
    query_string = urlencode(params)
    print(f"\n📝 Step 2: Create query string")
    print(f"   Query String: {query_string}")
    
    # Step 3: Generate signature
    signature = hmac.new(
        api_secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    
    print(f"\n📝 Step 3: Generate signature")
    print(f"   HMAC input (secret): {api_secret[:20]}...")
    print(f"   HMAC input (message): {query_string}")
    print(f"   Signature: {signature}")
    
    # Step 4: Check encoding
    print(f"\n📝 Step 4: Check encodings")
    print(f"   API Secret bytes: {api_secret.encode('utf-8')[:20]}...")
    print(f"   Query String bytes: {query_string.encode('utf-8')}")
    
    # Compare with expected format
    print(f"\n✅ Final request would be:")
    print(f"   URL: https://testnet.binancefuture.com/fapi/v2/account?{query_string}&signature={signature}")
    print(f"   Headers:")
    print(f"      X-MBX-APIKEY: {api_key}")
    
    # Possible issues
    print(f"\n🔍 Possible issues to check:")
    print(f"   1. Is API key valid and enabled on Binance testnet?")
    print(f"   2. Is API secret exactly correct (no spaces, extra chars)?")
    print(f"   3. Is this a testnet key (not mainnet)?")
    print(f"   4. Is timestamp within ±1000ms of server?")
    
    # Test with explicit values
    print(f"\n📝 Testing with explicit values:")
    test_secret = api_secret
    test_query = query_string
    test_sig = hmac.new(
        test_secret.encode("utf-8"),
        test_query.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    print(f"   Signature matches: {test_sig == signature}")

if __name__ == "__main__":
    test_signature()
