from utils.constants import ItemCategory

async def generate_photo_checklist(category: ItemCategory, defects: str) -> str:
    """
    MOCK-СЕРВИС: Захардкоженные подсказки под ограниченный набор категорий.
    (В финальной версии здесь должна быть динамическая генерация)
    """
    checklist = [
        "1️⃣ Общий план вещи при хорошем дневном свете."
    ]
    
    if category == ItemCategory.STROLLER:
        checklist.extend([
            "2️⃣ Фото в сложенном и разложенном виде.",
            "3️⃣ Крупно колеса и механизм тормоза.",
            "4️⃣ Внутренняя обивка крупным планом."
        ])
    elif category == ItemCategory.CLOTHES:
        checklist.extend([
            "2️⃣ Фото бирки с размером и составом.",
            "3️⃣ Крупно манжеты, воротник или коленки (там чаще следы носки)."
        ])
    elif category == ItemCategory.SHOES:
        checklist.extend([
            "2️⃣ Фото подошвы, чтобы был виден износ.",
            "3️⃣ Носы ботинок крупным планом."
        ])
    elif category == ItemCategory.TOYS:
        checklist.extend([
            "2️⃣ Фото включенной игрушки (если работает от батареек).",
            "3️⃣ Все комплектующие в одном кадре."
        ])
    else:
        checklist.extend([
            "2️⃣ Фото со всех сторон.",
            "3️⃣ Бирки или логотипы, если есть."
        ])
        
    low_defects = defects.lower().strip()
    if low_defects not in ["нет", "нету", "без дефектов", "идеально", "идеальная"]:
        checklist.append("⚠️ <b>Обязательно:</b> сделайте крупно фото дефекта, чтобы избежать возврата!")
        
    return "\n".join(checklist)
