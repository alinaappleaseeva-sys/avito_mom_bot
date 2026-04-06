from utils.constants import ItemCategory, ItemCondition
from utils.texts import CATEGORIES, CONDITIONS

async def generate_sales_text(category: ItemCategory, condition: ItemCondition, size: str, brand: str, defects: str) -> str:
    """
    Генерирует продающий текст для объявления на основе эвристик.
    """
    ru_category = CATEGORIES.get(category.value, "Вещь")
    title = f"{ru_category} {brand if brand.lower() != 'не знаю' else ''}".strip()
    
    lines = [
        f"Продаю {title.lower()} в связи с тем, что мы выросли из этого возраста.",
        ""
    ]
    
    if category == ItemCategory.STROLLER:
        lines.append("Очень удобная и маневренная коляска, зимой отлично справилась.")
    elif category == ItemCategory.CLOTHES:
        lines.append("Очень удобная в носке вещь, ребенку было комфортно.")
    elif category == ItemCategory.SHOES:
        lines.append("Теплая и надежная обувь, ни разу не подвела.")
    else:
        lines.append("Классная вещь, нам очень нравилась.")
        
    ru_condition = CONDITIONS.get(condition.value, condition.value)
    lines.extend([
        "",
        f"Состояние: {ru_condition}",
        f"Размер / Возраст: {size}"
    ])
    
    if brand.lower() != 'не знаю':
        lines.append(f"Бренд: {brand}")

    lines.append("")
    
    low_defects = defects.lower().strip()
    if low_defects in ["нет", "нету", "без дефектов", "идеально", "идеальная"]:
        lines.append("Идеальная вещь, без пятен, дыр и потертостей. Носили очень аккуратно.")
    else:
        lines.append("Есть небольшие минусы, но нам было удобно и так. Все остальное в порядке:")
        lines.append(f"- {defects.capitalize()}")
        lines.append("В цене это уже учтено.")
        
    lines.append("")
    lines.append("Пишите, отвечу на все вопросы. Возможна Авито.Доставка.")
    
    return "\n".join(lines)
