from aiogram import Router
import aiogram
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from utils.texts import MESSAGES

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(MESSAGES["start"])

@router.message(Command("delete_account"))
async def cmd_delete_account(message: Message):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да, удалить навсегда", callback_data="confirm_delete_account")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_delete_account")]
    ])
    await message.answer("⚠️ Внимание! Вы собираетесь удалить свой аккаунт и все сохраненные вещи. Это действие необратимо. Вы уверены?", reply_markup=markup)

@router.callback_query(lambda c: c.data == "confirm_delete_account")
async def process_confirm_delete_account(callback: aiogram.types.CallbackQuery):
    from database.crud import delete_user_account
    from database.errors import DatabaseError
    try:
        success = await delete_user_account(callback.from_user.id)
        if success:
            await callback.message.edit_text("Ваш аккаунт и все данные успешно удалены. До свидания!")
        else:
            await callback.message.edit_text("Не удалось найти ваш аккаунт для удаления.")
    except DatabaseError:
         await callback.message.edit_text("Произошла ошибка при удалении аккаунта. Попробуйте позже.")

@router.callback_query(lambda c: c.data == "cancel_delete_account")
async def process_cancel_delete_account(callback: aiogram.types.CallbackQuery):
    await callback.message.edit_text("Удаление отменено.")
