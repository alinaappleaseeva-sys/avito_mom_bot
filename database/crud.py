from sqlalchemy.future import select
from sqlalchemy import update, delete
from database.database import async_session
from database.models import User, Item

async def _get_or_create_user(telegram_id: int):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalars().first()
        if not user:
            user = User(telegram_id=telegram_id)
            session.add(user)
            await session.commit()
        return user

async def save_item(telegram_id: int, category: str, title: str, description: str, price: int):
    await _get_or_create_user(telegram_id)
    async with async_session() as session:
        new_item = Item(
            user_id=telegram_id,
            category=category,
            title=title,
            description=description,
            price=price,
            status="pending"
        )
        session.add(new_item)
        await session.commit()
        return new_item

async def get_user_items(telegram_id: int):
    async with async_session() as session:
        result = await session.execute(select(Item).where(Item.user_id == telegram_id).order_by(Item.created_at.desc()))
        return result.scalars().all()

async def update_item_url(item_id: int, user_id: int, url: str):
    async with async_session() as session:
        stmt = update(Item).where(Item.id == item_id, Item.user_id == user_id).values(avito_url=url, status="active")
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0

async def get_item_by_id(item_id: int, user_id: int):
    async with async_session() as session:
        result = await session.execute(select(Item).where(Item.id == item_id, Item.user_id == user_id))
        return result.scalars().first()

async def delete_item(item_id: int, user_id: int):
    async with async_session() as session:
        stmt = delete(Item).where(Item.id == item_id, Item.user_id == user_id)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0
