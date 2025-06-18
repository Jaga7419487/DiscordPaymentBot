import asyncio
import httpx
from constants import KOYEB_PUBLIC_LINK


async def ping_bot():
    while True:
        try:
            async with httpx.AsyncClient() as client:
                await client.get(f"{KOYEB_PUBLIC_LINK}/keep_alive")
        except Exception as e:
            print(f"Keep-alive request failed: {e}")
        await asyncio.sleep(300)
