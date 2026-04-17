from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from services.reports import generate_weekly_report
from database.errors import DatabaseError
from utils.texts import DB_ERROR_MESSAGE

router = Router()

@router.message(Command("report"))
@router.message(F.text.lower() == "отчет")
async def get_report(message: Message):
    msg = await message.answer("⏳ Собираю свежую статистику... это может занять несколько секунд.")
    
    try:
        report_text = await generate_weekly_report(message.from_user.id)
    except DatabaseError:
        await msg.delete()
        await message.answer(DB_ERROR_MESSAGE)
        return
    
    await msg.delete()
    if report_text:
        await message.answer(report_text, parse_mode="HTML")
    else:
        await message.answer("У вас пока нет 'Активных' вещей для отчета. Вы можете добавить ссылки к вещам в разделе /my_items.")
