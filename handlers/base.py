from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from utils.texts import MESSAGES

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(MESSAGES["start"])
