async def generate_sales_text(category: str, condition: str, size: str, brand: str, defects: str) -> str:
    """
    Генерирует продающий текст для объявления на основе эвристик.
    """
    title = f"{category} {brand if brand.lower() != 'не знаю' else ''}".strip()
    
    lines = [
        f"Продаю {title.lower()} в связи с тем, что мы выросли из этого возраста.",
        ""
    ]
    
    # Позитивный опыт использования
    if category == "Коляски":
        lines.append("Очень удобная и маневренная коляска, зимой отлично справилась.")
    elif category == "Одежда":
        lines.append("Очень удобная в носке вещь, ребенку было комфортно.")
    elif category == "Обувь":
        lines.append("Теплая и надежная обувь, ни разу не подвела.")
    else:
        lines.append("Классная вещь, нам очень нравилась.")
        
    lines.extend([
        "",
        f"Состояние: {condition}",
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
