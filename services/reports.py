import logging
from datetime import datetime, timezone
from database.crud import get_user_items, update_item_sync
from services.avito_client import avito_client, AvitoAPIError
from config import config

FRESH_ITEM_DAYS_THRESHOLD = 2
HIGH_VIEWS_THRESHOLD = 20

logger = logging.getLogger(__name__)

async def generate_weekly_report(telegram_id: int) -> str | None:
    items = await get_user_items(telegram_id)
    active_items = [item for item in items if item.status == "active"]
    
    if not active_items:
        return None
        
    lines = ["📊 <b>Ваш еженедельный отчет по активным вещам:</b>\n"]
    now = datetime.now(timezone.utc)
    
    for item in active_items:
        views = item.views or 0
        contacts = item.contacts or 0
        data_source = "🔴 Нет данных"
        
        # Попытка получить свежие данные, если есть ID
        if item.avito_item_id:
            if config.AVITO_API_MODE == "mock":
                data_source = "🟣 Режим эмуляции"
            
            try:
                stats = await avito_client.get_listing_stats(item.avito_item_id)
                views = stats.views
                contacts = stats.contacts
                
                # Обновляем кэш в БД
                await update_item_sync(item.id, telegram_id, views=views, contacts=contacts)
                
                if config.AVITO_API_MODE != "mock":
                    data_source = "🟢 Актуально с Авито"
            except AvitoAPIError as e:
                logger.warning(f"Failed to fetch stats for report (Item: {item.id}): {e}")
                if config.AVITO_API_MODE != "mock":
                    data_source = "🟡 Кэш"
        
        lines.append(f"📦 <b>{item.title}</b> ({item.price} руб.)")
        lines.append(f"👁 Просмотры: {views} | 💬 Контакты: {contacts} <i>{data_source}</i>")
        
        # Эвристика: Рекомендации
        created_at = item.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        days_active = (now - created_at).days
        
        if days_active < FRESH_ITEM_DAYS_THRESHOLD and views == 0:
            lines.append("💡 <i>Рекомендация:</i> Объявление совсем свежее, статистика еще не собралась. Подождем пару дней.")
        elif views == 0:
            lines.append("💡 <i>Рекомендация:</i> Совсем нет просмотров. Возможно, выбрана непопулярная категория, стоит обновить основное фото или предложить вещь бесплатно.")
        elif views > HIGH_VIEWS_THRESHOLD and contacts == 0:
            lines.append("💡 <i>Рекомендация:</i> Просмотры есть, обращений нет. Попробуйте обновить фотографии или немного снизить цену.")
        elif contacts > 0:
            lines.append("💡 <i>Рекомендация:</i> 🔥 Идут запросы! Не забывайте отвечать на сообщения (или звонки).")
        else:
            lines.append("💡 <i>Рекомендация:</i> 📊 Средняя динамика, ждем своего покупателя.")
            
        lines.append("")
        
    lines.append("Жду вас через неделю с новыми результатами! Успешных продаж! 💸")
    
    return "\n".join(lines)
