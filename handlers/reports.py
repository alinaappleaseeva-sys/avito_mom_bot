from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from services.reports import generate_weekly_report

router = Router()

@router.message(Command("report"))
@router.message(F.text.lower() == "отчет")
async def get_report(message: Message):
    msg = await message.answer("⏳ Собираю статистику с Авито (мок)...")
    
    report_text = await generate_weekly_report(message.fromuser.id if hasattr(message, 'fromuser') else message.from_user.id)
    
    await msg.delete()
    if report_text:
        await message.answer(report_text, parse_mode="HTML")
    else:
        await message.answer("У вас пока нет 'Активных' вещей для отчета. Вы можете добавить ссылки к вещам в разделе /my_items.")
