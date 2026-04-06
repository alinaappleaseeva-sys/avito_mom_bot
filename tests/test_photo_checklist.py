import pytest
from utils.constants import ItemCategory
from services.photo_checklist import generate_photo_checklist

@pytest.mark.asyncio
async def test_generate_photo_checklist_stroller_no_defects():
    checklist = await generate_photo_checklist(ItemCategory.STROLLER, defects="нет")
    assert "колеса и механизм тормоза" in checklist
    assert "дефекта" not in checklist

@pytest.mark.asyncio
async def test_generate_photo_checklist_clothes_with_defects():
    checklist = await generate_photo_checklist(ItemCategory.CLOTHES, defects="пятно на рукаве")
    assert "бирки с размером" in checklist
    assert "⚠️ <b>Обязательно:</b> сделайте крупно фото дефекта" in checklist
