import pytest
import hmac
import hashlib
import json
import time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from utils.telegram_init_data import validate_telegram_init_data, InvalidInitDataError
from database.crud import get_or_create_user_from_telegram
from database.models import User, Base
from config import config

pytestmark = pytest.mark.asyncio

# ----------------------------
# 1. Tests for initData validation
# ----------------------------
def generate_valid_init_data(bot_token: str, auth_date: int) -> str:
    user_payload = json.dumps({
        "id": 123456789,
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser"
    })
    
    # We must construct a dictionary, sort it and sign it exactly like Telegram does.
    params = {
        "auth_date": str(auth_date),
        "query_id": "AAHdF6IQAAAAA...",
        "user": user_payload
    }
    
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    hash_signature = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    
    # Build query string
    from urllib.parse import urlencode
    params["hash"] = hash_signature
    return urlencode(params)

def test_validate_telegram_init_data_success():
    bot_token = "12345:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    now = int(time.time())
    init_data = generate_valid_init_data(bot_token, now)
    
    user = validate_telegram_init_data(init_data, bot_token)
    assert user["id"] == 123456789
    assert user["username"] == "testuser"
    assert user["first_name"] == "Test"

def test_validate_telegram_init_data_expired():
    bot_token = "12345:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    # Create token 10 minutes ago
    expired_time = int(time.time()) - 600
    init_data = generate_valid_init_data(bot_token, expired_time)
    
    with pytest.raises(InvalidInitDataError, match="expired"):
        validate_telegram_init_data(init_data, bot_token, max_age=300)

def test_validate_telegram_init_data_invalid_hash():
    bot_token = "12345:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    now = int(time.time())
    init_data = generate_valid_init_data(bot_token, now)
    
    # tampered hash
    tampered_data = init_data.replace("hash=", "hash=fail")
    with pytest.raises(InvalidInitDataError, match="hash signature"):
        validate_telegram_init_data(tampered_data, bot_token)


# ----------------------------
# 2. Tests for get_or_create_user_from_telegram
# ----------------------------
@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session

async def test_get_or_create_user_is_not_admin(db_session, monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_ADMIN_ID", 9999)
    
    user = await get_or_create_user_from_telegram(
        db_session,
        telegram_id=111,
        username="normie",
        is_admin=False
    )
    
    assert user.telegram_id == 111
    assert user.role == "user"

async def test_get_or_create_user_is_admin_by_flag(db_session, monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_ADMIN_ID", 9999)
    
    user = await get_or_create_user_from_telegram(
        db_session,
        telegram_id=222,
        username="boss",
        is_admin=True
    )
    
    assert user.telegram_id == 222
    assert user.role == "admin"

async def test_get_or_create_user_is_admin_by_config(db_session, monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_ADMIN_ID", 333)
    
    user = await get_or_create_user_from_telegram(
        db_session,
        telegram_id=333,
        username="superadmin",
        is_admin=False
    )
    
    assert user.telegram_id == 333
    assert user.role == "admin"
    
async def test_get_user_existing_does_not_override_role(db_session, monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_ADMIN_ID", 9999)
    # create as admin
    user1 = await get_or_create_user_from_telegram(
        db_session,
        telegram_id=444,
        username="dude",
        is_admin=True
    )
    assert user1.role == "admin"
    
    # second call with is_admin=False should not demote if user is fetched
    user2 = await get_or_create_user_from_telegram(
        db_session,
        telegram_id=444,
        username="dude",
        is_admin=False
    )
    assert user2.id == user1.id
    assert user2.role == "admin" # stays admin
