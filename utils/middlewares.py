import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit_seconds: int = 1):
        self.limit_seconds = limit_seconds
        self.user_timestamps = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        if user_id is not None:
            now = asyncio.get_event_loop().time()
            last_time = self.user_timestamps.get(user_id, 0)
            
            if now - last_time < self.limit_seconds:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                if isinstance(event, Message):
                     await event.answer("Помедленнее! Я не успеваю. Пожалуйста, подождите немного.")
                elif isinstance(event, CallbackQuery):
                     await event.answer("Слишком много действий! Подождите...", show_alert=True)
                return
            
            self.user_timestamps[user_id] = now
            
        return await handler(event, data)
