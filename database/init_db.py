import asyncio
import sys
from sqlalchemy.exc import SQLAlchemyError
from database.database import create_db_and_tables
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def init_database():
    """Инициализирует базу данных вне жизненного цикла самого бота"""
    logger.info("Initializing database tables...")
    try:
        await create_db_and_tables()
        logger.info("Database tables initialized successfully!")
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(init_database())
