import pytest
from utils.constants import ItemCategory, ItemCondition
from services.text_generator import generate_sales_text

@pytest.mark.asyncio
async def test_generate_sales_text_no_defects():
    text = await generate_sales_text(
        category=ItemCategory.TOYS,
        condition=ItemCondition.NEW,
        size="для 3 лет",
        brand="LEGO",
        defects="без дефектов"
    )
    assert "Продаю игрушки lego" in text.lower() # title generation
    assert "Идеальная вещь, без пятен" in text

@pytest.mark.asyncio
async def test_generate_sales_text_with_defects():
    text = await generate_sales_text(
        category=ItemCategory.CLOTHES,
        condition=ItemCondition.GOOD,
        size="98",
        brand="Мазекея",
        defects="зацепка"
    )
    assert "Есть небольшие минусы" in text
    assert "- Зацепка" in text
