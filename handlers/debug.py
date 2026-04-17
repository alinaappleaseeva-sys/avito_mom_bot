import time
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from config import config
from database.models import Item
from services.avito_client import avito_client, AvitoAPIError
from utils.filters import IsAdminFilter

logger = setup_logger(__name__)
router = Router()

@router.message(Command("debug_avito_ping"), IsAdminFilter())
async def debug_ping(message: Message):
    
    await message.answer("🔧 Пингую Avito API (получение токена)...")
    try:
        success = await avito_client.ping()
        if success:
            await message.answer(f"✅ Токен успешно получен (ping OK)! Режим: {config.AVITO_API_MODE}")
        else:
            await message.answer(f"❌ Ошибка ping (auth failed).")
    except AvitoAPIError as e:
        await message.answer(f"❌ Ошибка ping: {e}")

@router.message(Command("debug_avito_test_listing"), IsAdminFilter())
async def debug_test_listing(message: Message):
        
    await message.answer(f"🔧 Начинаю тестовую публикацию в режиме {config.AVITO_API_MODE}...")
    
    # Required fields explicitly provided per current Avito Mapper rules.
    # If the mapper changes to require things like 'city' or 'condition', add them here!
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
