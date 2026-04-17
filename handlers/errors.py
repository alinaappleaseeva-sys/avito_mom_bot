from aiogram import Router
from aiogram.types import ErrorEvent
from utils.logger import setup_logger
import asyncio
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from database.errors import DatabaseError

logger = setup_logger(__name__)
router = Router()

@router.errors()
async def global_error_handler(event: ErrorEvent):
    """
    Глобальный обработчик ошибок. Если возникает исключение:
    1. Логируем ошибку с трейсбеком
    2. Если возможно, уведомляем пользователя, чтобы диалог не зависал
    """
    exc = event.exception
    logger.exception("An exception occurred in aiogram handler!", exc_info=exc)
    
    # Специфические сообщения для таймаутов и базы данных
    error_message = "❌ Упс! Произошла техническая ошибка на стороне сервера.\nПопробуйте начать заново через /cancel или /start."
    if isinstance(exc, (SQLAlchemyError, OperationalError, DatabaseError, asyncio.TimeoutError)):
        error_message = "Сервис временно недоступен, мы уже чиним базу. Попробуйте, пожалуйста, ещё раз через несколько минут."
    
    # Пытаемся отправить сообщение об ошибке, если апдейт содержит message, callback_query и т.д.
    if event.update.message:
        try:
            await event.update.message.answer(error_message)
        except Exception:
            pass
    elif event.update.callback_query:
        try:
            await event.update.callback_query.answer(error_message, show_alert=True)
        except Exception:
            pass
