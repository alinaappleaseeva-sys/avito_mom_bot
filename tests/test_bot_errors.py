import pytest
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from unittest.mock import AsyncMock, patch

from handlers.active_items import show_my_items
from database.errors import DatabaseError
from utils.texts import DB_ERROR_MESSAGE

pytestmark = pytest.mark.asyncio

async def test_bot_active_items_db_error_handling(monkeypatch):
    """
    Проверка, что падение БД при /my_items перехватывается 
    совершенно корректно и отдает юзеру DB_ERROR_MESSAGE.
    """
    message_mock = AsyncMock(spec=Message)
    message_mock.from_user = AsyncMock()
    message_mock.from_user.id = 123
    
    # Мокаем crud функцию, пробрасывая ошибку БД
    async def mock_get_user_items(*args, **kwargs):
        raise DatabaseError("Mock database failure")
        
    import handlers.active_items
    monkeypatch.setattr(handlers.active_items, "get_user_items", mock_get_user_items)
    
    # Вызываем целевой хендлер
    await show_my_items(message_mock)
    
    # Проверяем, что бот ответил стандартной фразой
    message_mock.answer.assert_called_once_with(DB_ERROR_MESSAGE)

