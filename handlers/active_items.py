from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database.crud import get_user_items, update_item_url, delete_item, update_item_status
from database.errors import DatabaseError
from services.avito_client import avito_client, AvitoAPIError
from utils.constants import ItemStatus
from services.avito_mapper import map_avito_status_to_domain

router = Router()

class LinkForm(StatesGroup):
    waiting_for_url = State()

@router.message(Command("my_items"))
@router.message(F.text.lower() == "мои вещи")
async def show_my_items(message: Message):
    try:
        items = await get_user_items(message.from_user.id)
    except DatabaseError:
        await message.answer("Сейчас есть техническая проблема, попробуйте позже.")
        return
        
    if not items:
        await message.answer("У вас пока нет сохраненных вещей. Добавьте новую через /add !")
        return
        
    await message.answer("Ваши вещи:")
    for item in items:
        # Fallback for old data DB values without doing full migration
        db_status = item.status
        if db_status == "pending": db_status = ItemStatus.DRAFT.value
        if db_status == "on_review": db_status = ItemStatus.PENDING_MODERATION.value

        # Fetch new status if Avito Item ID is present
        reject_reason = None
        if item.avito_item_id:
            try:
                info = await avito_client.get_item_info(item.avito_item_id)
                avito_status = info.get("status")
                if avito_status:
                    new_domain_status = map_avito_status_to_domain(avito_status)
                    reject_reason = info.get("reject_reason")
                    if new_domain_status != db_status:
                        await update_item_status(item.id, message.from_user.id, new_domain_status)
                        db_status = new_domain_status
            except AvitoAPIError:
                pass # Proceed with existing db_status if api fails

        # Determing UI
        if db_status == ItemStatus.DRAFT.value:
            status_emoji = "📝"
            status_text = "Черновик (ожидает публикации)"
        elif db_status == ItemStatus.PENDING_MODERATION.value:
            status_emoji = "🧐"
            status_text = "На проверке (Авито проверяет объявление)"
        elif db_status == ItemStatus.ACTIVE.value:
            status_emoji = "✅"
            status_text = "Активно (продается)"
        elif db_status == ItemStatus.REJECTED.value:
            status_emoji = "❌"
            status_text = "Отклонено"
            if reject_reason:
                status_text += f"\nПричина: <i>{reject_reason}</i>"
        elif db_status == ItemStatus.ARCHIVED.value:
            status_emoji = "🗄️"
            status_text = "В архиве"
        else:
            status_emoji = "❓"
            status_text = "Неизвестно"

        text = f"{status_emoji} <b>{item.title}</b>\nЦена: {item.price} руб.\nСтатус: {status_text}"
        
        markup = None
        if db_status == ItemStatus.DRAFT.value:
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Добавить ссылку вручную", callback_data=f"add_link_{item.id}")],
                [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_item_{item.id}")]
            ])
        else:
            if db_status == ItemStatus.ACTIVE.value:
                if item.avito_url:
                    text += f"\nСсылка: {item.avito_url}"
                if item.avito_item_id:
                    try:
                        stats = await avito_client.get_listing_stats(item.avito_item_id)
                        text += f"\n👁️ Просмотров: {stats['views']} | 💬 Контактов: {stats['contacts']}"
                    except AvitoAPIError:
                        text += "\n👁️ Просмотров: недоступно | 💬 Контактов: недоступно (Ошибка)"
            
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_item_{item.id}")]
            ])
            
        await message.answer(text, reply_markup=markup, parse_mode="HTML")

@router.callback_query(F.data.startswith("add_link_"))
async def process_add_link_callback(callback: CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[2])
    await state.update_data(item_id=item_id)
    await state.set_state(LinkForm.waiting_for_url)
    await callback.message.answer(
        "Пришлите мне ссылку на опубликованное объявление (или нажмите /cancel для отмены):"
    )
    await callback.answer()

@router.message(LinkForm.waiting_for_url)
async def process_url_input(message: Message, state: FSMContext):
    data = await state.get_data()
    item_id = data["item_id"]
    url = message.text
    
    from urllib.parse import urlparse
    
    if len(url) > 200:
        await message.answer("Ссылка слишком длинная. Убедитесь, что вы скопировали правильную ссылку.")
        return

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        await message.answer("Неверный формат ссылки. Убедитесь, что это http/https ссылка.")
        return

    if parsed.netloc != "avito.ru" and not parsed.netloc.endswith(".avito.ru"):
        await message.answer("Кажется, это не ссылка на Авито. Попробуйте еще раз или нажмите /cancel.")
        return
        
    try:
        success = await update_item_url(item_id, message.from_user.id, url)
        if success:
            await message.answer("Отлично! Ссылка сохранена, вещь теперь в статусе 'Продается'. Я начну собирать по ней статистику раз в неделю.")
        else:
            await message.answer("Произошла ошибка при сохранении ссылки.")
    except DatabaseError:
        await message.answer("Сейчас есть техническая проблема, попробуйте позже.")
        
    await state.clear()

@router.callback_query(F.data.startswith("delete_item_"))
async def process_delete_item_callback(callback: CallbackQuery):
    item_id = int(callback.data.split("_")[2])
    try:
        success = await delete_item(item_id, callback.from_user.id)
        if success:
            await callback.message.delete()
            await callback.answer("Вещь успешно удалена!", show_alert=True)
        else:
            await callback.answer("Не удалось удалить вещь.", show_alert=True)
    except DatabaseError:
        await callback.answer("Сейчас есть техническая проблема, попробуйте позже.", show_alert=True)
