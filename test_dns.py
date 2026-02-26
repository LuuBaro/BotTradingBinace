
import asyncio
import aiohttp
import socket
import sys

async def test_connection(url):
    print(f"Testing connection to: {url}")
    
    # 1. DNS Resolution
    hostname = url.replace("https://", "").split("/")[0]
    try:
        ip = socket.gethostbyname(hostname)
        print(f"✅ DNS resolution ok: {hostname} -> {ip}")
    except socket.gaierror as e:
        print(f"❌ DNS resolution failed for {hostname}: {e}")
        return

    # 2. HTTP Request
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                print(f"✅ HTTP request ok: Status {response.status}")
    except Exception as e:
        print(f"❌ HTTP request failed: {e}")

if __name__ == "__main__":
    urls = [
        "https://testnet.binancefuture.com/fapi/v1/time",
        "https://fapi.binance.com/fapi/v1/time"
    ]
    for url in urls:
        asyncio.run(test_connection(url))
