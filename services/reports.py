import random
from database.crud import get_user_items

async def generate_weekly_report(telegram_id: int) -> str | None:
    items = await get_user_items(telegram_id)
    active_items = [item for item in items if item.status == "active"]
    
    if not active_items:
        return None
        
    lines = ["📊 <b>Ваш еженедельный отчет по активным вещам:</b>\n"]
    
    for item in active_items:
        # Генерируем моковую статистику
        views = random.randint(5, 100)
        favorites = int(views * random.uniform(0.05, 0.2))
        messages = random.randint(0, 3) if views > 30 else 0
        
        lines.append(f"📦 <b>{item.title}</b> ({item.price} руб.)")
        lines.append(f"👁 Просмотры: {views} | ❤️ В избранном: {favorites} | ✉️ Сообщения: {messages}")
        
        # Эвристика: Рекомендации
        if views < 15:
            lines.append("💡 <i>Рекомендация:</i> Мало просмотров. Попробуйте обновить главное фото или снизить цену на 10%.")
        elif favorites > 5 and messages == 0:
            lines.append("💡 <i>Рекомендация:</i> Вещь часто добавляют в избранное, но не пишут. Возможно, цена чуть завышена, скиньте 5-10% — и ее заберут!")
        elif messages > 0:
            lines.append("💡 <i>Рекомендация:</i> Идут диалоги! Будьте на связи. Если никто не забрал, можно предложить скидку в личных сообщениях.")
        else:
            lines.append("💡 <i>Рекомендация:</i> Хорошая динамика, пока ничего не трогайте. Ожидаем продажу!")
            
        lines.append("")
        
    lines.append("Жду вас через неделю с новыми результатами! Успешных продаж! 💸")
    
    return "\n".join(lines)
