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
# TODO: Использовать CONDITION_MAP в payload, когда Avito API (через атрибуты) будет это поддерживать,
#       и когда свойство condition будет добавлено в БД-модель Item.
# CONDITION_MAP = {
#     ItemCondition.NEW: "Новое",
#     ItemCondition.PERFECT: "Б/у",
#     ItemCondition.GOOD: "Б/у",
#     ItemCondition.FAIR: "Б/у"
# }

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
        
    # TODO: Добавить поле city в модель Item. Пока проверяем наличие атрибута, иначе используем хардкод.
    city = getattr(item, 'city', None)
    if not city:
        logger.warning("Атрибут city отсутствует у Item. Используется fallback город 'Москва'.")
        city = "Москва"
        
    payload = {
        "title": item.title,
        "description": item.description,
        "price": item.price,
        "category": avito_category,
        "location": {
            "address": city
        }
    }
    
    # Добавление расширенных параметров в будущем (состояние, размер) будет зависеть 
    # от расширения доменной модели Item
    
    return payload
