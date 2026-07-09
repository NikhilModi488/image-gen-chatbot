import asyncio
import httpx

import urllib.parse

async def test_pollinations():
    prompts = [
        "A cute cat wearing a wizard hat",
        "A futuristic neon city in the rain"
    ]
    
    # Try different URL formulations
    urls = [
        # Simplified URL
        lambda p: f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p)}",
        # Custom dimensions
        lambda p: f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p)}?width=800&height=600&nologo=true",
        # Full URL
        lambda p: f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p)}?width=800&height=600&nologo=true&private=true"
    ]

    
    async with httpx.AsyncClient(timeout=20.0) as client:
        for p in prompts:
            print(f"\nTesting prompt: '{p}'")
            for i, url_fn in enumerate(urls):
                url = url_fn(p)
                print(f"  Attempt {i+1}: GET {url}")
                try:
                    res = await client.get(url)
                    print(f"    Status Code: {res.status_code}")
                    if res.status_code == 200:
                        content_type = res.headers.get("content-type", "")
                        print(f"    Success! Content-Type: {content_type}, Length: {len(res.content)} bytes")
                    else:
                        print(f"    Response body: {res.text[:100]}")
                except Exception as e:
                    print(f"    Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_pollinations())
