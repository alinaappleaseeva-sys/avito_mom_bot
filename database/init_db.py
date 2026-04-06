import asyncio
import logging
from database.database import create_db_and_tables

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_database():
    """Инициализирует базу данных вне жизненного цикла самого бота"""
    logger.info("Initializing database tables...")
    await create_db_and_tables()
    logger.info("Database tables initialized successfully!")

if __name__ == "__main__":
    asyncio.run(init_database())
