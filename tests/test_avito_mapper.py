import pytest
from utils.constants import ItemCategory, ItemStatus
from services.avito_mapper import CATEGORY_MAP, map_avito_status_to_domain

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

def test_map_avito_status_to_domain():
    assert map_avito_status_to_domain("active") == ItemStatus.ACTIVE.value
    assert map_avito_status_to_domain("moderation") == ItemStatus.PENDING_MODERATION.value
    assert map_avito_status_to_domain("in_moderation") == ItemStatus.PENDING_MODERATION.value
    assert map_avito_status_to_domain("rejected") == ItemStatus.REJECTED.value
    assert map_avito_status_to_domain("blocked") == ItemStatus.REJECTED.value
    assert map_avito_status_to_domain("old") == ItemStatus.ARCHIVED.value
    assert map_avito_status_to_domain("draft") == ItemStatus.DRAFT.value
    
    # Check normalization
    assert map_avito_status_to_domain(" Active ") == ItemStatus.ACTIVE.value
    assert map_avito_status_to_domain("REJECTED") == ItemStatus.REJECTED.value
    
    # Check arbitrary random strings should fallback to Draft
    assert map_avito_status_to_domain("some_random_status") == ItemStatus.DRAFT.value
