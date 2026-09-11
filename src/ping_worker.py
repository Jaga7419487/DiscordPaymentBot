import asyncio

import httpx

from config_logger import get_logger
from constants import KOYEB_PUBLIC_LINK

logger = get_logger(__name__)

async def ping_bot():
    while True:
        try:
            async with httpx.AsyncClient() as client:
                await client.get(f"{KOYEB_PUBLIC_LINK}/keep_alive")
        except Exception:
            logger.exception("Keep-alive request failed")
        await asyncio.sleep(300)
