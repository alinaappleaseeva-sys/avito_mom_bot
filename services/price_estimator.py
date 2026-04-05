import random

async def estimate_price_and_time(category: str, condition: str, defect_status: str, speed: str) -> tuple[int, str]:
    """
    Мок-функция для оценки стоимости и срока продажи вещи.
    Возвращает: (рекомендуемая цена, ожидаемый срок продажи)
    """
    # Базовые цены в зависимости от категории
    base_prices = {
        "Коляски": random.randint(5000, 20000),
        "Одежда": random.randint(500, 3000),
        "Обувь": random.randint(800, 2500),
        "Игрушки": random.randint(300, 4000),
        "Другое": random.randint(500, 2000)
    }

    price = base_prices.get(category, 1000)

    # Корректировка цены по состоянию
    if condition.startswith("Новая"):
        price = int(price * 1.5)
    elif condition.startswith("Идеальное"):
        price = int(price * 1.0)
    elif condition.startswith("Хорошее"):
        price = int(price * 0.7)
    else:  # Удовлетворительное
        price = int(price * 0.4)

    # Если есть дефекты (не равны 'Нет', 'нету', 'идеально' и тд)
    low_defects = defect_status.lower().strip()
    if low_defects not in ["нет", "нету", "без дефектов", "идеально", "идеальная"]:
        price = int(price * 0.8)

    # Скорость продажи влияет на цену и срок
    if speed == "Как можно быстрее":
        price = int(price * 0.8) # скидка за скорость
        time_to_sell = "1-3 дня"
    else:
        time_to_sell = "1-2 недели"
        
    price = int(price * 0.8) # общее снижение на 20% по опыту пользователя
        
    return price, time_to_sell
