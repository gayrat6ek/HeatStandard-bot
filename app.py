import asyncio
import logging
import sys
from loader import dp, bot
from handlers.users import start, menu, order, inline
from handlers import admin

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting bot...")

    dp.include_router(inline.router)  # Must be first to catch inline queries
    dp.include_router(admin.router)   # Admin callback handlers
    dp.include_router(menu.router)    # Menu button handlers
    dp.include_router(order.router)   # Order flow handlers
    dp.include_router(start.router)   # Start/registration handlers (LAST - has catch-all)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
