import pytest
from utils.constants import ItemCategory, ItemCondition, SellSpeed
from services.price_estimator import estimate_price_and_time

@pytest.mark.asyncio
async def test_estimate_price_and_time_new():
    price, time_to_sell = await estimate_price_and_time(
        category=ItemCategory.STROLLER,
        condition=ItemCondition.NEW,
        defect_status="нет",
        speed=SellSpeed.OPTIMAL
    )
    assert price > 0
    assert time_to_sell == "1-2 недели"

@pytest.mark.asyncio
async def test_estimate_price_and_time_fast_speed():
    price, time_to_sell = await estimate_price_and_time(
        category=ItemCategory.SHOES,
        condition=ItemCondition.FAIR,
        defect_status="царапины",
        speed=SellSpeed.FAST
    )
    assert price > 0
    assert time_to_sell == "1-3 дня"
