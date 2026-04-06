from aiogram import Router
from aiogram.types import ErrorEvent
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = Router()

@router.errors()
async def global_error_handler(event: ErrorEvent):
    """
    Глобальный обработчик ошибок. Если возникает исключение:
    1. Логируем ошибку с трейсбеком
    2. Если возможно, уведомляем пользователя, чтобы диалог не зависал
    """
    logger.exception("An exception occurred in aiogram handler!", exc_info=event.exception)
    
    # Пытаемся отправить сообщение об ошибке, если апдейт содержит message, callback_query и т.д.
    if event.update.message:
        try:
            await event.update.message.answer(
                "❌ Упс! Произошла техническая ошибка на стороне сервера.\nПопробуйте начать заново через /cancel или /start."
            )
        except Exception:
            pass
    elif event.update.callback_query:
        try:
            await event.update.callback_query.answer("Произошла ошибка при обработке.")
        except Exception:
            pass
