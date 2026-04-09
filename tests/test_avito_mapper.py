import pytest
from utils.constants import ItemCategory
from services.avito_mapper import CATEGORY_MAP

def test_avito_mapper_has_all_categories():
    """
    Убеждаемся, что CATEGORY_MAP содержит маппинг для каждого значения Enum(ItemCategory).
    Это предотвращает молчаливый откат на fallback (прочее) при добавлении новых категорий в БД/домен.
    """
    missing_categories = []
    
    for category in ItemCategory:
        if category not in CATEGORY_MAP:
            missing_categories.append(category)
            
    assert not missing_categories, f"Следующие категории отсутствуют в CATEGORY_MAP: {missing_categories}"
