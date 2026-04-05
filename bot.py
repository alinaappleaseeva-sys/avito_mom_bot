import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import config
from database.database import create_db_and_tables
from handlers import base, add_item, active_items, reports

# Инициализация логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Создаем таблицы в БД
    await create_db_and_tables()

    # Создаем объекты бота и диспетчера
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    # Регистрируем роутеры хендлеров
    dp.include_router(base.router)
    dp.include_router(add_item.router)
    dp.include_router(active_items.router)
    dp.include_router(reports.router)

    # Пропускаем накопившиеся апдейты и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")
