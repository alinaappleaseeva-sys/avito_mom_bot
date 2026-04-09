from typing import Dict, Any
from utils.constants import ItemCategory, ItemCondition
from database.models import Item
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Справочник категорий Авито (упрощенный вариант для MVP)
CATEGORY_MAP = {
    ItemCategory.STROLLER: "Детские коляски",
    ItemCategory.CLOTHES: "Детская одежда",
    ItemCategory.SHOES: "Детская обувь",
    ItemCategory.TOYS: "Игрушки",
    ItemCategory.OTHER: "Товары для детей и игрушки / прочее"
}

# Справочник состояний (Пока не сохраняется в БД Item напрямую, но оставляем для расширения интеграции)
CONDITION_MAP = {
    ItemCondition.NEW: "Новое",
    ItemCondition.PERFECT: "Б/у",
    ItemCondition.GOOD: "Б/у",
    ItemCondition.FAIR: "Б/у"
}

def build_avito_payload_for_item(item: Item) -> Dict[str, Any]:
    """
    Конвертирует нашу доменную модель Item в структуру данных (payload) для создания объявления на Авито.
    :param item: объект sqlalchemy модели Item
    :return: dict-payload для Avito API
    """
    avito_category = CATEGORY_MAP.get(item.category)
    if not avito_category:
        logger.warning(f"Маппинг для категории '{item.category}' не найден. По умолчанию ставим 'Детские товары и игрушки / прочее'.")
        avito_category = "Товары для детей и игрушки / прочее"
        
    payload = {
        "title": item.title,
        "description": item.description,
        "price": item.price,
        "category": avito_category,
        "location": {
            "address": "Москва" # Хардкод для MVP, согласно одобренному плану
        }
    }
    
    # Добавление расширенных параметров в будущем (состояние, размер) будет зависеть 
    # от расширения доменной модели Item
    
    return payload
