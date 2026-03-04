#!/usr/bin/env python3
"""
Quick fix: Manually set BINANCE_TESTNET_TIME_OFFSET in .env
This is a workaround solution until system time is synced
"""
import asyncio
import time
import hashlib
import hmac
from urllib.parse import urlencode
import aiohttp

async def get_correct_offset():
    """Calculate correct offset between local and Binance server"""
    connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            # Multiple samples to get better average
            offsets = []
            for i in range(3):
                before = int(time.time() * 1000)
                async with session.get("https://testnet.binancefuture.com/fapi/v1/time") as resp:
                    data = await resp.json()
                after = int(time.time() * 1000)
                
                server_ts = data.get("serverTime")
                local_ts = (before + after) // 2
                offset = server_ts - local_ts
                offsets.append(offset)
                print(f"Sample {i+1}: offset = {offset}ms")
            
            avg_offset = sum(offsets) // len(offsets)
            print(f"\n✓ Average offset: {avg_offset}ms")
            print(f"✓ Add this to .env: MANUAL_TIMESTAMP_OFFSET={avg_offset}")
            return avg_offset
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

if __name__ == "__main__":
    offset = asyncio.run(get_correct_offset())
    if offset:
        print(f"\n📝 To fix this, add to .env:")
        print(f"   MANUAL_TIMESTAMP_OFFSET={offset}")
