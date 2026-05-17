import asyncio
import logging
import os
import glob
from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

# إصلاح Pyrogram لبايثون 3.10+
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from config import Client

# حذف جلسات قديمة
for f in glob.glob("my_bot*"):
    try:
        os.remove(f)
    except Exception:
        pass


# ── Health-check server (aiohttp — نفس event loop، لا thread إضافي) ────
async def _health(request):
    return web.Response(text="✅ Bot is running")

async def _start_health_server():
    port = int(os.environ.get("PORT", 10000))
    app  = web.Application()
    app.router.add_get("/", _health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Health-check server on port %d", port)


async def main():
    from Plugins.auto_clean import _auto_clean_loop

    await _start_health_server()

    async with Client:
        me = await Client.get_me()
        logger.info("البوت شغال: @%s", me.username)

        asyncio.get_running_loop().create_task(_auto_clean_loop(Client))
        logger.info("حلقة التنظيف التلقائي تعمل")

        await asyncio.sleep(float("inf"))


if __name__ == "__main__":
    loop.run_until_complete(main())
