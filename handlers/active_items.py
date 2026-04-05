from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database.crud import get_user_items, update_item_url, delete_item

router = Router()

class LinkForm(StatesGroup):
    waiting_for_url = State()

@router.message(Command("my_items"))
@router.message(F.text.lower() == "мои вещи")
async def show_my_items(message: Message):
    items = await get_user_items(message.from_user.id)
    if not items:
        await message.answer("У вас пока нет сохраненных вещей. Добавьте новую через /add !")
        return
        
    await message.answer("Ваши вещи:")
    for item in items:
        status_emoji = "⏳" if item.status == "pending" else "✅"
        text = f"{status_emoji} <b>{item.title}</b>\nЦена: {item.price} руб."
        
        if item.status == "pending":
            text += "\nСтатус: ожидает публикации (нет ссылки)."
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Добавить ссылку с Авито", callback_data=f"add_link_{item.id}")],
                [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_item_{item.id}")]
            ])
        else:
            text += f"\nСтатус: продается.\nСсылка: {item.avito_url}"
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
    
    if "avito.ru" not in url.lower():
        await message.answer("Кажется, это не ссылка на Авито. Попробуйте еще раз или нажмите /cancel.")
        return
        
    success = await update_item_url(item_id, message.from_user.id, url)
    if success:
        await message.answer("Отлично! Ссылка сохранена, вещь теперь в статусе 'Продается'. Я начну собирать по ней статистику раз в неделю.")
    else:
        await message.answer("Произошла ошибка при сохранении ссылки.")
        
    await state.clear()

@router.callback_query(F.data.startswith("delete_item_"))
async def process_delete_item_callback(callback: CallbackQuery):
    item_id = int(callback.data.split("_")[2])
    success = await delete_item(item_id, callback.from_user.id)
    if success:
        await callback.message.delete()
        await callback.answer("Вещь успешно удалена!", show_alert=True)
    else:
        await callback.answer("Не удалось удалить вещь.", show_alert=True)
