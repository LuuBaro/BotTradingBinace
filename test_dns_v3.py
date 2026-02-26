
import asyncio
import aiohttp
import socket

async def test_threaded_resolver(url):
    print(f"Testing with ThreadedResolver to: {url}")
    # Force threaded resolver (system resolver)
    connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url, timeout=10) as response:
                print(f"✅ ThreadedResolver ok: Status {response.status}")
    except Exception as e:
        print(f"❌ ThreadedResolver failed: {e}")

if __name__ == "__main__":
    url = "https://testnet.binancefuture.com/fapi/v1/time"
    asyncio.run(test_threaded_resolver(url))
