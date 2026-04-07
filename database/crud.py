import logging
from sqlalchemy.future import select
from sqlalchemy import update, delete
from sqlalchemy.exc import SQLAlchemyError
from database.database import async_session
from database.models import User, Item
from database.errors import DatabaseError
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def _get_or_create_user(telegram_id: int):
    try:
        async with async_session() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalars().first()
            if not user:
                user = User(telegram_id=telegram_id)
                session.add(user)
                await session.commit()
            return user
    except SQLAlchemyError as e:
        logger.error(f"DB Error getting/creating user {telegram_id}: {e}")
        raise DatabaseError(f"Failed to get or create user: {e}")

async def save_item(telegram_id: int, category: str, title: str, description: str, price: int):
    await _get_or_create_user(telegram_id)
    try:
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
    except SQLAlchemyError as e:
        logger.error(f"DB Error saving item for user {telegram_id}: {e}")
        raise DatabaseError(f"Failed to save item: {e}")

async def get_user_items(telegram_id: int):
    try:
        async with async_session() as session:
            result = await session.execute(select(Item).where(Item.user_id == telegram_id).order_by(Item.created_at.desc()))
            return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(f"DB Error getting user items for {telegram_id}: {e}")
        raise DatabaseError(f"Failed to retrieve user items: {e}")

async def update_item_url(item_id: int, user_id: int, url: str):
    try:
        async with async_session() as session:
            stmt = update(Item).where(Item.id == item_id, Item.user_id == user_id).values(avito_url=url, status="active")
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    except SQLAlchemyError as e:
        logger.error(f"DB Error updating item {item_id}: {e}")
        raise DatabaseError(f"Failed to update item URL: {e}")

async def get_item_by_id(item_id: int, user_id: int):
    try:
        async with async_session() as session:
            result = await session.execute(select(Item).where(Item.id == item_id, Item.user_id == user_id))
            return result.scalars().first()
    except SQLAlchemyError as e:
        logger.error(f"DB Error getting item {item_id}: {e}")
        raise DatabaseError(f"Failed to retrieve item details: {e}")

async def delete_item(item_id: int, user_id: int):
    try:
        async with async_session() as session:
            stmt = delete(Item).where(Item.id == item_id, Item.user_id == user_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    except SQLAlchemyError as e:
        logger.error(f"DB Error deleting item {item_id}: {e}")
        raise DatabaseError(f"Failed to delete item: {e}")

async def update_item_avito_id(item_id: int, user_id: int, avito_item_id: str):
    try:
        async with async_session() as session:
            stmt = update(Item).where(Item.id == item_id, Item.user_id == user_id).values(avito_item_id=avito_item_id, status="active")
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    except SQLAlchemyError as e:
        logger.error(f"DB Error updating avito_item_id for item {item_id}: {e}")
        raise DatabaseError(f"Failed to update Avito Item ID: {e}")
