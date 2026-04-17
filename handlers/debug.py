import time
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from config import config
from database.models import Item
from services.avito_client import avito_client, AvitoAPIError
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = Router()

def is_admin(message: Message) -> bool:
    return message.from_user.id == config.TELEGRAM_ADMIN_ID

@router.message(Command("debug_avito_ping"))
async def debug_ping(message: Message):
    if not is_admin(message):
        return
    
    await message.answer("🔧 Пингую Avito API (получение токена)...")
    try:
        # accessing private method for debug intent
        token = await avito_client._get_access_token()
        await message.answer(f"✅ Токен успешно получен! Режим: {config.AVITO_API_MODE}")
    except AvitoAPIError as e:
        await message.answer(f"❌ Ошибка Auth: {e}")

@router.message(Command("debug_avito_test_listing"))
async def debug_test_listing(message: Message):
    if not is_admin(message):
        return
        
    await message.answer(f"🔧 Начинаю тестовую публикацию в режиме {config.AVITO_API_MODE}...")
    
    dummy_item = Item(
        telegram_id=message.from_user.id,
        category="other",
        title="[ТЕСТ] Тестовый заголовок",
        description="Тестовое описание, созданное автоматизированной системой. Не покупайте.",
        price=100
    )
    
    try:
        item_id = await avito_client.create_listing(dummy_item)
        await message.answer(f"✅ Тестовое объявление создано! Avito ID: {item_id}\nПытаюсь снять с публикации...")
        
        success = await avito_client.archive_listing(str(item_id))
        if success:
            await message.answer("✅ Объявление успешно отправлено в архив/закрыто!")
        else:
            await message.answer("⚠️ Не удалось архивировать объявление из-за ошибки API (проверьте логи).")
            
    except AvitoAPIError as e:
        await message.answer(f"❌ Ошибка загрузки тест-объявления: {e}")
