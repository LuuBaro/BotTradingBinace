
import asyncio
import aiohttp
import socket
import requests

def test_requests(url):
    print(f"Testing with REQUESTS (sync) to: {url}")
    try:
        response = requests.get(url, timeout=10)
        print(f"✅ Requests ok: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Requests failed: {e}")

async def test_aiohttp_default(url):
    print(f"Testing with AIOHTTP (default) to: {url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                print(f"✅ aiohttp default ok: Status {response.status}")
    except Exception as e:
        print(f"❌ aiohttp default failed: {e}")

async def test_aiohttp_no_dns_cache(url):
    print(f"Testing with AIOHTTP (no dns cache, IPv4 forced) to: {url}")
    connector = aiohttp.TCPConnector(use_dns_cache=False, family=socket.AF_INET)
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url, timeout=10) as response:
                print(f"✅ aiohttp customized ok: Status {response.status}")
    except Exception as e:
        print(f"❌ aiohttp customized failed: {e}")

if __name__ == "__main__":
    url = "https://testnet.binancefuture.com/fapi/v1/time"
    test_requests(url)
    asyncio.run(test_aiohttp_default(url))
    asyncio.run(test_aiohttp_no_dns_cache(url))
