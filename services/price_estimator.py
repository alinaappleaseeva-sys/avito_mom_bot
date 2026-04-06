import random
from utils.constants import ItemCategory, ItemCondition, SellSpeed

async def estimate_price_and_time(category: ItemCategory, condition: ItemCondition, defect_status: str, speed: SellSpeed) -> tuple[int, str]:
    """
    MOCK-СЕРВИС: Временная логика оценки стоимости и срока продажи вещи.
    (В финальной версии здесь должен быть вызов AI или API аналитики Авито)
    Возвращает: (рекомендуемая цена, ожидаемый срок продажи)
    """
    # Используем детерминированный генератор случайных чисел для стабильности MVP сессии
    seed_string = f"{category.value}_{condition.value}_{defect_status.lower().strip()}_{speed.value}"
    rng = random.Random(seed_string)

    base_prices = {
        ItemCategory.STROLLER: rng.randint(5000, 20000),
        ItemCategory.CLOTHES: rng.randint(500, 3000),
        ItemCategory.SHOES: rng.randint(800, 2500),
        ItemCategory.TOYS: rng.randint(300, 4000),
        ItemCategory.OTHER: rng.randint(500, 2000)
    }

    price = base_prices.get(category, 1000)

    if condition == ItemCondition.NEW:
        price = int(price * 1.5)
    elif condition == ItemCondition.PERFECT:
        price = int(price * 1.0)
    elif condition == ItemCondition.GOOD:
        price = int(price * 0.7)
    else:
        price = int(price * 0.4)

    low_defects = defect_status.lower().strip()
    if low_defects not in ["нет", "нету", "без дефектов", "идеально", "идеальная"]:
        price = int(price * 0.8)

    if speed == SellSpeed.FAST:
        price = int(price * 0.8)
        time_to_sell = "1-3 дня"
    else:
        time_to_sell = "1-2 недели"
        
    price = int(price * 0.8)
        
    return price, time_to_sell
