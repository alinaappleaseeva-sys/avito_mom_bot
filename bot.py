import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import config
from handlers import base, add_item, active_items, reports, errors, debug
from utils.logger import setup_logger

# Инициализация логгера
logger = setup_logger(__name__)

async def main():
    # Создаем объекты бота и диспетчера
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    # Инициализация и регистрация middleware для rate-limit
    from utils.middlewares import RateLimitMiddleware
    dp.message.middleware(RateLimitMiddleware(limit_seconds=1))
    dp.callback_query.middleware(RateLimitMiddleware(limit_seconds=1))

    # Регистрируем роутеры хендлеров
    dp.include_router(errors.router) # Перехватчик ошибок регистрируется первым
    dp.include_router(base.router)
    dp.include_router(add_item.router)
    dp.include_router(active_items.router)
    dp.include_router(reports.router)
    dp.include_router(debug.router)

    from services.avito_client import avito_client
    from scripts.migrate_statuses import migrate_db
    
    migrate_db()

    # Пропускаем накопившиеся апдейты и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot started!")
    
    await avito_client.start()
    try:
        await dp.start_polling(bot)
    finally:
        await avito_client.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")
