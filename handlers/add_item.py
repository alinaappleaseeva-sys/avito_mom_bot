from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from utils.texts import MESSAGES, CATEGORIES, CONDITIONS, SPEEDS, CANCEL_BTN, CATEGORIES_REVERSE, CONDITIONS_REVERSE, SPEEDS_REVERSE
from utils.constants import ItemCategory, ItemCondition, SellSpeed
from services.price_estimator import estimate_price_and_time
from services.text_generator import generate_sales_text
from services.photo_checklist import generate_photo_checklist
from database.crud import save_item, update_item_avito_id, get_item_by_id
from database.errors import DatabaseError
from utils.logger import setup_logger
from services.avito_client import avito_client, AvitoAPIError
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

logger = setup_logger(__name__)

router = Router()

class ItemForm(StatesGroup):
    category = State()
    condition = State()
    size = State()
    brand = State()
    defects = State()
    speed = State()

def make_keyboard(items: list[str]) -> ReplyKeyboardMarkup:
    """Создает клавиатуру с кнопками из списка и добавляет кнопку отмены."""
    buttons = [[KeyboardButton(text=item)] for item in items]
    buttons.append([KeyboardButton(text=CANCEL_BTN)])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=CANCEL_BTN)]],
    resize_keyboard=True
)

@router.message(F.text == CANCEL_BTN)
@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    """Позволяет отменить создание объявления на любом шаге."""
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.clear()
    await message.answer(MESSAGES["cancel"], reply_markup=ReplyKeyboardRemove())

@router.message(Command("add"))
@router.message(F.text.lower() == "добавить вещь")
async def start_add_item(message: Message, state: FSMContext):
    """Начало сценария добавления вещи."""
    from config import config
    if config.AVITO_API_MODE == "sandbox":
        await message.answer("Бот находится на техобслуживании, создание объявлений временно приостановлено.")
        return
        
    await state.set_state(ItemForm.category)
    await message.answer(
        MESSAGES["ask_category"],
        reply_markup=make_keyboard(list(CATEGORIES.values()))
    )

@router.message(ItemForm.category)
async def process_category(message: Message, state: FSMContext):
    category_ru = message.text
    if category_ru not in CATEGORIES_REVERSE:
         logger.warning(f"User {message.from_user.id} chose invalid category: {category_ru}")
         await message.answer("Пожалуйста, выберите вариант из клавиатуры.")
         return
    
    await state.update_data(category=CATEGORIES_REVERSE[category_ru])
    await state.set_state(ItemForm.condition)
    await message.answer(
        MESSAGES["ask_condition"],
        reply_markup=make_keyboard(list(CONDITIONS.values()))
    )

@router.message(ItemForm.condition)
async def process_condition(message: Message, state: FSMContext):
    condition_ru = message.text
    if condition_ru not in CONDITIONS_REVERSE:
         logger.warning(f"User {message.from_user.id} chose invalid condition: {condition_ru}")
         await message.answer("Пожалуйста, выберите вариант из клавиатуры.")
         return
         
    await state.update_data(condition=CONDITIONS_REVERSE[condition_ru])
    await state.set_state(ItemForm.size)
    await message.answer(
        MESSAGES["ask_size"],
        reply_markup=cancel_keyboard
    )

@router.message(ItemForm.size)
async def process_size(message: Message, state: FSMContext):
    if message.text and len(message.text) > 50:
        await message.answer("Слишком длинный текст для размера (макс. 50 символов). Пожалуйста, напишите короче.")
        return
        
    await state.update_data(size=message.text)
    await state.set_state(ItemForm.brand)
    
    brand_keyboard = make_keyboard(["Не знаю"])
    await message.answer(
        MESSAGES["ask_brand"],
        reply_markup=brand_keyboard
    )

@router.message(ItemForm.brand)
async def process_brand(message: Message, state: FSMContext):
    if message.text and len(message.text) > 100:
        await message.answer("Слишком длинное название бренда (макс. 100 символов). Пожалуйста, напишите короче.")
        return
        
    await state.update_data(brand=message.text)
    await state.set_state(ItemForm.defects)
    
    defects_keyboard = make_keyboard(["Нет"])
    await message.answer(
        MESSAGES["ask_defects"],
        reply_markup=defects_keyboard
    )

@router.message(ItemForm.defects, F.photo)
async def process_defects_photo(message: Message, state: FSMContext):
    # Rule 20: Limit upload sizes
    photo = message.photo[-1]
    if photo.file_size and photo.file_size > 5 * 1024 * 1024:
        await message.answer("Фото слишком большое! Пожалуйста, загрузите фото размером до 5 МБ.")
        return

    # Мок обработки фото(vision API)
    mock_defect_description = "следы использования (определено по фото)"
    await state.update_data(defects=mock_defect_description)
    await state.set_state(ItemForm.speed)
    await message.answer(
        f"Ого, вижу на фото дефект. Чтобы не задерживать, я пока записал его как: '{mock_defect_description}'. В будущем я смогу описывать их точнее!\n\n" + MESSAGES["ask_speed"],
        reply_markup=make_keyboard(list(SPEEDS.values()))
    )

@router.message(ItemForm.defects, F.text)
async def process_defects_text(message: Message, state: FSMContext):
    if message.text and len(message.text) > 500:
        await message.answer("Слишком длинное описание дефектов (макс. 500 символов). Пожалуйста, будьте кратки.")
        return
        
    await state.update_data(defects=message.text)
    await state.set_state(ItemForm.speed)
    await message.answer(
        MESSAGES["ask_speed"],
        reply_markup=make_keyboard(list(SPEEDS.values()))
    )

@router.message(ItemForm.speed)
async def process_speed(message: Message, state: FSMContext):
    speed_ru = message.text
    if speed_ru not in SPEEDS_REVERSE:
        logger.warning(f"User {message.from_user.id} chose invalid speed: {speed_ru}")
        await message.answer("Пожалуйста, выберите вариант из клавиатуры.")
        return
        
    speed_eng = SPEEDS_REVERSE[speed_ru]
    await state.update_data(speed=speed_eng)
    
    # 1. Показываем статус загрузки
    msg = await message.answer(MESSAGES["generating"], reply_markup=ReplyKeyboardRemove())
    
    # Сбор всех данных
    data = await state.get_data()
    
    category_val = ItemCategory(data["category"])
    condition_val = ItemCondition(data["condition"])
    speed_val = SellSpeed(data["speed"])

    # 2. Обработка через сервисы-моки
    price, time_to_sell = await estimate_price_and_time(
        category_val, condition_val, data["defects"], speed_val
    )
    
    text = await generate_sales_text(
        category_val, condition_val, data["size"], data["brand"], data["defects"]
    )
    
    checklist = await generate_photo_checklist(category_val, data["defects"])
    
    # Сохраняем в базу данных (Шаг 4)
    try:
        item = await save_item(
            telegram_id=message.from_user.id,
            category=data["category"],
            title=f"{CATEGORIES[data['category']]} {data['brand'] if data['brand'].lower() != 'не знаю' else ''}".strip(),
            description=text,
            price=price
        )
    except DatabaseError:
        await msg.delete()
        await message.answer("Сейчас есть техническая проблема с сохранением объявления, попробуйте позже.", reply_markup=ReplyKeyboardRemove())
        return
    
    # Формируем финальный результат
    final_text = MESSAGES["result_template"].format(
        price=price,
        time_to_sell=time_to_sell,
        text=text,
        photo_checklist=checklist
    )
    final_text += f"\n\n✅ <b>Вещь пока сохранена в черновик (ID: {item.id})!</b>"
    
    publish_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Опубликовать на Авито сейчас", callback_data=f"publish_{item.id}")],
        [InlineKeyboardButton(text="💾 Оставить в черновиках", callback_data=f"draft_{item.id}")]
    ])
    
    # 3. Отправляем результат
    await msg.delete()
    await message.answer(final_text, reply_markup=publish_markup, parse_mode="HTML")
    
    # Очищаем состояние
    await state.clear()

@router.callback_query(F.data.startswith("publish_"))
async def process_publish_callback(callback: CallbackQuery):
    from config import config
    if config.AVITO_API_MODE == "sandbox":
        await callback.answer("Бот находится на техобслуживании, создание объявлений временно приостановлено.", show_alert=True)
        return
        
    item_id = int(callback.data.split("_")[1])
    
    try:
        item = await get_item_by_id(item_id, callback.from_user.id)
        if not item:
            await callback.answer("Вещь не найдена.", show_alert=True)
            return
            
        await callback.message.edit_reply_markup(reply_markup=None) # Убираем кнопки
        msg = await callback.message.answer("⏳ Отправляю запросы к Авито API...")
        
        avito_id = await avito_client.create_listing(item)
        
        await update_item_avito_id(item_id, callback.from_user.id, avito_id)
        await msg.edit_text(f"✅ Ура! Объявление успешно отправлено на Авито и сейчас находится на модерации (avito_item_id: {avito_id})!\nЕго статус можно отслеживать в разделе /my_items.")
        
    except AvitoAPIError as e:
        logger.error(f"Avito publish error for user {callback.from_user.id}: {e}")
        await msg.edit_text(f"❌ Похоже, вашему профилю недоступна прямая публикация через API, либо произошла ошибка Авито.\nПодробности: {e}\n\nПожалуйста, выставите объявление вручную и прикрепите ссылку в меню /my_items !")
    except DatabaseError:
        await msg.edit_text("Объявление опубликовано на Авито, но произошла ошибка сохранения его ID в нашу базу данных.")
        
@router.callback_query(F.data.startswith("draft_"))
async def process_draft_callback(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Окей, вещь ждет вас в разделе /my_items. Вы сможете опубликовать ее позже вручную.")
    await callback.answer()
