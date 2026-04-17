from sqlalchemy import Column, Integer, String, BigInteger, DateTime
from sqlalchemy.sql import func
from database.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    role = Column(String, nullable=False, default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True) # Reference to User.telegram_id
    category = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    status = Column(String, default="draft") # draft, pending_moderation, active, rejected, archived, unknown
    avito_url = Column(String, nullable=True)
    avito_item_id = Column(String, nullable=True) # ID from Avito API
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    views = Column(Integer, default=0)
    contacts = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
