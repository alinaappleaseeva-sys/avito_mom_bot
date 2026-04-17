import logging
from sqlalchemy.future import select
from sqlalchemy import update, delete
from sqlalchemy.sql import func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from database.database import async_session
from database.models import User, Item
from database.errors import DatabaseError
from utils.constants import ItemStatus
from utils.logger import setup_logger

logger = setup_logger(__name__)

from config import config

async def get_user_by_telegram_id(session, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalars().first()

async def create_user(
    session, 
    telegram_id: int, 
    username: str = None, 
    first_name: str = None, 
    last_name: str = None, 
    role: str = "user"
) -> User:
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        role=role
    )
    session.add(user)
    await session.commit()
    return user

async def get_or_create_user_from_telegram(
    session, 
    *, 
    telegram_id: int, 
    username: str = None, 
    first_name: str = None, 
    last_name: str = None, 
    is_admin: bool = False
) -> User:
    user = await get_user_by_telegram_id(session, telegram_id)
    if user:
        return user
    
    role = "admin" if is_admin or telegram_id == config.TELEGRAM_ADMIN_ID else "user"
    try:
        return await create_user(
            session,
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=role
        )
    except IntegrityError:
        # Race condition: user was created via another concurrent request
        await session.rollback()
        user = await get_user_by_telegram_id(session, telegram_id)
        if user:
            return user
        raise

async def _get_or_create_user(telegram_id: int):
    """Legacy helper for existing bot handlers, uses dedicated session."""
    try:
        async with async_session() as session:
            user = await get_user_by_telegram_id(session, telegram_id)
            if not user:
                user = await create_user(session, telegram_id=telegram_id)
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
                status=ItemStatus.DRAFT.value
            )
            session.add(new_item)
            await session.commit()
            logger.info(f"User {telegram_id} created a new item: {new_item.id}")
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
            stmt = update(Item).where(Item.id == item_id, Item.user_id == user_id).values(avito_url=url, status=ItemStatus.ACTIVE.value)
            result = await session.execute(stmt)
            await session.commit()
            if result.rowcount > 0:
                logger.info(f"User {user_id} updated URL for item {item_id}")
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
            if result.rowcount > 0:
                logger.info(f"User {user_id} deleted item {item_id}")
            return result.rowcount > 0
    except SQLAlchemyError as e:
        logger.error(f"DB Error deleting item {item_id}: {e}")
        raise DatabaseError(f"Failed to delete item: {e}")

async def update_item_avito_id(item_id: int, user_id: int, avito_item_id: str):
    try:
        async with async_session() as session:
            stmt = update(Item).where(Item.id == item_id, Item.user_id == user_id).values(avito_item_id=avito_item_id, status=ItemStatus.PENDING_MODERATION.value)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    except SQLAlchemyError as e:
        logger.error(f"DB Error updating avito_item_id for item {item_id}: {e}")
        raise DatabaseError(f"Failed to update Avito Item ID: {e}")

async def update_item_status(item_id: int, user_id: int, status: ItemStatus):
    try:
        async with async_session() as session:
            stmt = update(Item).where(Item.id == item_id, Item.user_id == user_id).values(status=status.value)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    except SQLAlchemyError as e:
        logger.error(f"DB Error updating status for item {item_id}: {e}")
        raise DatabaseError(f"Failed to update item status: {e}")

async def update_item_sync(item_id: int, user_id: int, status: ItemStatus = None, views: int = None, contacts: int = None):
    try:
        async with async_session() as session:
            values = {"last_synced_at": func.now()}
            if status is not None:
                values["status"] = status.value
            if views is not None:
                values["views"] = views
            if contacts is not None:
                values["contacts"] = contacts
            stmt = update(Item).where(Item.id == item_id, Item.user_id == user_id).values(**values)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    except SQLAlchemyError as e:
        logger.error(f"DB Error updating sync info for item {item_id}: {e}")
        raise DatabaseError(f"Failed to update item sync info: {e}")

async def delete_user_account(telegram_id: int):
    try:
        async with async_session() as session:
            # First, delete all user items
            await session.execute(delete(Item).where(Item.user_id == telegram_id))
            # Then delete the user
            result = await session.execute(delete(User).where(User.telegram_id == telegram_id))
            await session.commit()
            if result.rowcount > 0:
                logger.info(f"User {telegram_id} successfully deleted their account.")
            return result.rowcount > 0
    except SQLAlchemyError as e:
        logger.error(f"DB Error deleting account for user {telegram_id}: {e}")
        raise DatabaseError(f"Failed to delete user account: {e}")
