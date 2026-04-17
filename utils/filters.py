from aiogram.filters import BaseFilter
from aiogram.types import Message
from config import config
from database.database import async_session
from database.crud import get_user_by_telegram_id

class IsAdminFilter(BaseFilter):
    """
    Проверяет, является ли пользователь администратором.
    Сначала проверяется конфигурационный TELEGRAM_ADMIN_ID,
    а затем - роль 'admin' в таблице users.
    """
    async def __call__(self, message: Message) -> bool:
        if not message.from_user:
            return False
            
        telegram_id = message.from_user.id
        
        # Fast path
        if telegram_id == config.TELEGRAM_ADMIN_ID and config.TELEGRAM_ADMIN_ID != 0:
            return True
            
        # DB check
        async with async_session() as session:
            user = await get_user_by_telegram_id(session, telegram_id)
            if user and getattr(user, 'role', 'user') == "admin":
                return True
                
        return False

class IsAuthorizedUserFilter(BaseFilter):
    """
    Проверяет, зарегистрирован ли пользователь в базе данных.
    Может быть полезно для ограничения команд только для юзеров из Mini App.
    """
    async def __call__(self, message: Message) -> bool:
        if not message.from_user:
            return False
            
        telegram_id = message.from_user.id
        async with async_session() as session:
            user = await get_user_by_telegram_id(session, telegram_id)
            return user is not None
