import pytest
from utils.constants import ItemCategory, ItemCondition
from utils.texts import CATEGORIES_REVERSE, CONDITIONS_REVERSE

def test_mappings_valid():
    # Valid mapping string -> enum
    assert CATEGORIES_REVERSE["Коляски"] == ItemCategory.STROLLER.value
    assert CONDITIONS_REVERSE["Новая (с биркой)"] == ItemCondition.NEW.value

def test_mappings_invalid_shows_missing_key():
    # Test invalid string doesn't match and would cause KeyError if not handled safely
    assert "Неизвестная" not in CATEGORIES_REVERSE
    assert "Крокодил" not in CONDITIONS_REVERSE
