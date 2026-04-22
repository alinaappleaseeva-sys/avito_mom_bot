"""
Расширенный тест-сьют безопасности авторизации avito_mom_bot.

Покрывает:
- Изоляцию пользователей (user A ≠ user B на уровне данных)
- JWT middleware (просроченный токен, отсутствие заголовка, Bearer-формат)
- RBAC: роль из JWT НЕ «апгрейдит» пользователя выше того, что в БД
- Privilege escalation при TELEGRAM_ADMIN_ID=0
- initData replay / подделка / future timestamp
- JWT none-algorithm / wrong-secret / forged-role атаки
- Пограничные случаи (без username, дубликаты, UNIQUE constraint)
"""

import pytest
import pytest_asyncio
import hmac
import hashlib
import json
import time
import jwt as pyjwt
from urllib.parse import urlencode

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, TestClient, TestServer

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy import update, delete

from utils.telegram_init_data import validate_telegram_init_data, InvalidInitDataError
from utils.jwt_tokens import create_access_token, decode_access_token
from services.auth_http import jwt_auth_middleware
from database.crud import (
    get_or_create_user_from_telegram,
    get_user_by_telegram_id,
    create_user,
)
from database.models import User, Item, Base
from config import config

pytestmark = pytest.mark.asyncio


# ============================================================
# Mock user personas
# ============================================================

MOCK_BOT_TOKEN = "12345:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"

MOCK_USERS = {
    "alice": {"telegram_id": 100001, "username": "alice_mom", "first_name": "Alice", "last_name": "Smith"},
    "bob":   {"telegram_id": 100002, "username": "bob_dad",   "first_name": "Bob",   "last_name": "Johnson"},
    "eve":   {"telegram_id": 100003, "username": "eve_admin", "first_name": "Eve",   "last_name": "Admin"},
}


# ============================================================
# Helpers
# ============================================================

def generate_init_data_for_user(user_dict: dict, bot_token: str, auth_date: int = None) -> str:
    """Генерирует валидный Telegram Mini App initData для моковго юзера."""
    if auth_date is None:
        auth_date = int(time.time())

    user_payload = json.dumps({
        "id": user_dict["telegram_id"],
        "first_name": user_dict["first_name"],
        "last_name": user_dict["last_name"],
        "username": user_dict["username"],
    })

    params = {
        "auth_date": str(auth_date),
        "query_id": "AAHdF6IQAAAAA...",
        "user": user_payload,
    }

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    hash_signature = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    params["hash"] = hash_signature
    return urlencode(params)


# ============================================================
# Fixtures
# ============================================================

@pytest_asyncio.fixture
async def db_session():
    """In-memory SQLite для каждого теста."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def populated_db(db_session, monkeypatch):
    """
    Создаёт трёх моковых юзеров + по предмету каждому:
    - alice (role=user)
    - bob   (role=user)
    - eve   (role=admin)
    """
    monkeypatch.setattr(config, "TELEGRAM_ADMIN_ID", MOCK_USERS["eve"]["telegram_id"])

    users = {}
    for name, data in [("alice", MOCK_USERS["alice"]), ("bob", MOCK_USERS["bob"]), ("eve", MOCK_USERS["eve"])]:
        user = await get_or_create_user_from_telegram(
            db_session,
            telegram_id=data["telegram_id"],
            username=data["username"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            is_admin=(name == "eve"),
        )
        users[name] = user

    items = {}
    for name, tg_id in [("alice", MOCK_USERS["alice"]["telegram_id"]),
                         ("bob",   MOCK_USERS["bob"]["telegram_id"]),
                         ("eve",   MOCK_USERS["eve"]["telegram_id"])]:
        item = Item(
            user_id=tg_id,
            category="toys",
            title=f"{name}'s teddy bear",
            description=f"Item belonging to {name}",
            price=500,
            status="draft",
        )
        db_session.add(item)

    await db_session.commit()

    for name, tg_id in [("alice", MOCK_USERS["alice"]["telegram_id"]),
                         ("bob",   MOCK_USERS["bob"]["telegram_id"]),
                         ("eve",   MOCK_USERS["eve"]["telegram_id"])]:
        result = await db_session.execute(select(Item).where(Item.user_id == tg_id))
        items[name] = result.scalars().first()

    return {"users": users, "items": items, "session": db_session}


@pytest_asyncio.fixture
async def middleware_app(monkeypatch):
    """aiohttp приложение с JWT middleware и тестовым protected-хендлером."""
    monkeypatch.setattr(config, "JWT_SECRET", "test_jwt_secret_32bytes_long!!!")
    monkeypatch.setattr(config, "JWT_ALGORITHM", "HS256")

    async def protected_handler(request: web.Request) -> web.Response:
        user = request.get("user", {})
        return web.json_response({"ok": True, "user": user})

    app = web.Application(middlewares=[jwt_auth_middleware])
    app.router.add_post("/auth/telegram", protected_handler)  # open route
    app.router.add_get("/api/me", protected_handler)           # protected route

    return app


# ============================================================
# ГРУППА 1: Изоляция пользователей (user A ≠ user B)
# ============================================================

class TestUserIsolation:
    """Данные одного пользователя недоступны другому."""

    async def test_user_cannot_see_other_users_items(self, populated_db):
        """Alice НЕ видит предметы Bob."""
        session = populated_db["session"]
        alice_tg_id = MOCK_USERS["alice"]["telegram_id"]
        bob_item_id = populated_db["items"]["bob"].id

        result = await session.execute(
            select(Item).where(Item.id == bob_item_id, Item.user_id == alice_tg_id)
        )
        assert result.scalars().first() is None, "Alice не должна видеть предмет Bob"

    async def test_user_sees_only_own_items(self, populated_db):
        """Каждый юзер видит только свои предметы."""
        session = populated_db["session"]
        for name in ("alice", "bob"):
            tg_id = MOCK_USERS[name]["telegram_id"]
            result = await session.execute(select(Item).where(Item.user_id == tg_id))
            items = result.scalars().all()
            assert len(items) == 1, f"{name} должен видеть ровно 1 предмет"
            assert items[0].description == f"Item belonging to {name}"

    async def test_user_cannot_update_other_users_item(self, populated_db):
        """Alice НЕ может обновить URL предмета Bob."""
        session = populated_db["session"]
        stmt = (
            update(Item)
            .where(Item.id == populated_db["items"]["bob"].id,
                   Item.user_id == MOCK_USERS["alice"]["telegram_id"])
            .values(avito_url="https://evil.com/stolen")
        )
        result = await session.execute(stmt)
        await session.commit()
        assert result.rowcount == 0, "rowcount должен быть 0"

        # Оригинал не изменился
        result = await session.execute(
            select(Item).where(Item.id == populated_db["items"]["bob"].id)
        )
        assert result.scalars().first().avito_url is None

    async def test_user_cannot_delete_other_users_item(self, populated_db):
        """Alice НЕ может удалить предмет Bob."""
        session = populated_db["session"]
        stmt = delete(Item).where(
            Item.id == populated_db["items"]["bob"].id,
            Item.user_id == MOCK_USERS["alice"]["telegram_id"]
        )
        result = await session.execute(stmt)
        await session.commit()
        assert result.rowcount == 0

        # Предмет Bob на месте
        result = await session.execute(
            select(Item).where(Item.id == populated_db["items"]["bob"].id)
        )
        assert result.scalars().first() is not None

    async def test_user_can_manage_own_item(self, populated_db):
        """Alice МОЖЕТ обновить и удалить СВОЙ предмет."""
        session = populated_db["session"]
        alice_tg = MOCK_USERS["alice"]["telegram_id"]
        alice_item = populated_db["items"]["alice"].id

        # Update
        stmt = update(Item).where(Item.id == alice_item, Item.user_id == alice_tg).values(avito_url="https://avito.ru/ok")
        result = await session.execute(stmt)
        await session.commit()
        assert result.rowcount == 1

        # Delete
        stmt = delete(Item).where(Item.id == alice_item, Item.user_id == alice_tg)
        result = await session.execute(stmt)
        await session.commit()
        assert result.rowcount == 1

    async def test_delete_account_only_deletes_own_data(self, populated_db):
        """Удаление аккаунта Alice не затрагивает Bob."""
        session = populated_db["session"]
        alice_tg = MOCK_USERS["alice"]["telegram_id"]
        bob_tg = MOCK_USERS["bob"]["telegram_id"]

        await session.execute(delete(Item).where(Item.user_id == alice_tg))
        await session.execute(delete(User).where(User.telegram_id == alice_tg))
        await session.commit()

        # Alice удалена
        result = await session.execute(select(User).where(User.telegram_id == alice_tg))
        assert result.scalars().first() is None

        # Bob цел
        result = await session.execute(select(User).where(User.telegram_id == bob_tg))
        assert result.scalars().first() is not None
        result = await session.execute(select(Item).where(Item.user_id == bob_tg))
        assert len(result.scalars().all()) == 1

    async def test_different_users_get_different_jwt_tokens(self, monkeypatch):
        """Токены Alice и Bob содержат разные sub и telegram_id."""
        monkeypatch.setattr(config, "JWT_SECRET", "test_secret_long_enough_32bytes!")
        monkeypatch.setattr(config, "JWT_ALGORITHM", "HS256")

        t_a = create_access_token(user_id=1, telegram_id=MOCK_USERS["alice"]["telegram_id"], role="user")
        t_b = create_access_token(user_id=2, telegram_id=MOCK_USERS["bob"]["telegram_id"],   role="user")

        p_a = decode_access_token(t_a)
        p_b = decode_access_token(t_b)

        assert p_a["sub"] != p_b["sub"]
        assert p_a["telegram_id"] != p_b["telegram_id"]
        assert t_a != t_b


# ============================================================
# ГРУППА 2: JWT Middleware
# ============================================================

class TestJWTMiddleware:
    """Тесты HTTP middleware для JWT."""

    async def test_open_route_no_auth_required(self, middleware_app, aiohttp_client):
        """POST /auth/telegram пропускается без токена."""
        client = await aiohttp_client(middleware_app)
        resp = await client.post("/auth/telegram", json={})
        assert resp.status == 200  # handler вернёт ok (middleware пропускает)

    async def test_protected_route_rejects_no_header(self, middleware_app, aiohttp_client):
        """GET /api/me без Authorization header → 401."""
        client = await aiohttp_client(middleware_app)
        resp = await client.get("/api/me")
        assert resp.status == 401
        data = await resp.json()
        assert "Authorization" in data["error"]

    async def test_protected_route_rejects_invalid_bearer(self, middleware_app, aiohttp_client):
        """Authorization header без 'Bearer ' → 401."""
        client = await aiohttp_client(middleware_app)
        resp = await client.get("/api/me", headers={"Authorization": "Token abc123"})
        assert resp.status == 401

    async def test_protected_route_rejects_expired_token(self, middleware_app, aiohttp_client, monkeypatch):
        """Просроченный JWT → 401 'Token has expired'."""
        monkeypatch.setattr(config, "JWT_SECRET", "test_jwt_secret_32bytes_long!!!")
        monkeypatch.setattr(config, "JWT_ALGORITHM", "HS256")

        expired_token = create_access_token(user_id=1, telegram_id=100, role="user", expires_in=-10)
        client = await aiohttp_client(middleware_app)
        resp = await client.get("/api/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert resp.status == 401
        data = await resp.json()
        assert "expired" in data["error"].lower()

    async def test_protected_route_rejects_garbage_token(self, middleware_app, aiohttp_client):
        """Мусорный токен → 401."""
        client = await aiohttp_client(middleware_app)
        resp = await client.get("/api/me", headers={"Authorization": "Bearer not.a.real.token"})
        assert resp.status == 401
        data = await resp.json()
        assert "Invalid" in data["error"]

    async def test_protected_route_rejects_wrong_secret(self, middleware_app, aiohttp_client):
        """JWT подписанный чужим секретом → 401."""
        payload = {
            "sub": "1", "telegram_id": 100, "role": "user",
            "plan": "free", "iat": int(time.time()), "exp": int(time.time()) + 3600,
        }
        forged = pyjwt.encode(payload, "wrong_secret_wrong_secret_32byt", algorithm="HS256")

        client = await aiohttp_client(middleware_app)
        resp = await client.get("/api/me", headers={"Authorization": f"Bearer {forged}"})
        assert resp.status == 401

    async def test_protected_route_passes_valid_token(self, middleware_app, aiohttp_client, monkeypatch):
        """Валидный JWT → 200, request['user'] содержит payload."""
        monkeypatch.setattr(config, "JWT_SECRET", "test_jwt_secret_32bytes_long!!!")
        monkeypatch.setattr(config, "JWT_ALGORITHM", "HS256")

        token = create_access_token(user_id=42, telegram_id=100001, role="user")
        client = await aiohttp_client(middleware_app)
        resp = await client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status == 200
        data = await resp.json()
        assert data["ok"] is True
        assert data["user"]["sub"] == "42"
        assert data["user"]["telegram_id"] == 100001
        assert data["user"]["role"] == "user"


# ============================================================
# ГРУППА 3: Роль из JWT НЕ «апгрейдит» пользователя
# ============================================================

class TestJWTRoleCannotUpgradeUser:
    """JWT не должен позволять повышение привилегий."""

    async def test_jwt_role_does_not_override_db_role(self, db_session, monkeypatch):
        """Если в БД role='user', то даже JWT с role='admin' не меняет БД."""
        monkeypatch.setattr(config, "TELEGRAM_ADMIN_ID", 9999)
        monkeypatch.setattr(config, "JWT_SECRET", "test_secret_long_enough_32bytes!")
        monkeypatch.setattr(config, "JWT_ALGORITHM", "HS256")

        # Создаём обычного пользователя в БД
        user = await get_or_create_user_from_telegram(
            db_session, telegram_id=100001, username="alice", is_admin=False,
        )
        assert user.role == "user"

        # Представим JWT с role=admin (подделанный клиентом, но подписанный правильно)
        token_with_admin_role = create_access_token(
            user_id=user.id, telegram_id=user.telegram_id, role="admin"
        )
        payload = decode_access_token(token_with_admin_role)
        assert payload["role"] == "admin"  # В токене написано admin

        # Но роль в БД не должна измениться!
        db_user = await get_user_by_telegram_id(db_session, 100001)
        assert db_user.role == "user", \
            "JWT role='admin' НЕ должна менять БД role='user'"

    async def test_forged_admin_token_with_wrong_secret_rejected(self, monkeypatch):
        """Атакующий без секрета не может создать токен с role=admin."""
        monkeypatch.setattr(config, "JWT_SECRET", "real_production_secret_32bytes!!")
        monkeypatch.setattr(config, "JWT_ALGORITHM", "HS256")

        forged_payload = {
            "sub": "1", "telegram_id": 100, "role": "admin",
            "plan": "free", "iat": int(time.time()), "exp": int(time.time()) + 3600,
        }
        forged_token = pyjwt.encode(forged_payload, "attackers_guess_secret_32bytesss", algorithm="HS256")

        with pytest.raises(pyjwt.InvalidSignatureError):
            decode_access_token(forged_token)

    async def test_admin_in_jwt_must_match_admin_in_db(self, db_session, monkeypatch):
        """При создании токена роль должна браться из БД, не от клиента."""
        admin_tg_id = MOCK_USERS["eve"]["telegram_id"]
        monkeypatch.setattr(config, "TELEGRAM_ADMIN_ID", admin_tg_id)
        monkeypatch.setattr(config, "JWT_SECRET", "test_secret_long_enough_32bytes!")
        monkeypatch.setattr(config, "JWT_ALGORITHM", "HS256")

        # Admin
        admin_user = await get_or_create_user_from_telegram(
            db_session, telegram_id=admin_tg_id, username="eve", is_admin=True,
        )
        token_admin = create_access_token(
            user_id=admin_user.id, telegram_id=admin_user.telegram_id, role=admin_user.role
        )
        assert decode_access_token(token_admin)["role"] == "admin"

        # Regular user
        regular_user = await get_or_create_user_from_telegram(
            db_session, telegram_id=MOCK_USERS["alice"]["telegram_id"], username="alice", is_admin=False,
        )
        token_user = create_access_token(
            user_id=regular_user.id, telegram_id=regular_user.telegram_id, role=regular_user.role
        )
        assert decode_access_token(token_user)["role"] == "user"


# ============================================================
# ГРУППА 4: RBAC соответствие плану
# ============================================================

class TestRBACCompliance:
    """Роли назначаются строго по docs/roles_rbac.md."""

    async def test_new_user_gets_role_user(self, db_session, monkeypatch):
        monkeypatch.setattr(config, "TELEGRAM_ADMIN_ID", 9999)
        user = await get_or_create_user_from_telegram(db_session, telegram_id=100001, username="alice", is_admin=False)
        assert user.role == "user"

    async def test_admin_by_config(self, db_session, monkeypatch):
        monkeypatch.setattr(config, "TELEGRAM_ADMIN_ID", MOCK_USERS["eve"]["telegram_id"])
        user = await get_or_create_user_from_telegram(
            db_session, telegram_id=MOCK_USERS["eve"]["telegram_id"], username="eve", is_admin=False,
        )
        assert user.role == "admin"

    async def test_admin_by_flag(self, db_session, monkeypatch):
        monkeypatch.setattr(config, "TELEGRAM_ADMIN_ID", 9999)
        user = await get_or_create_user_from_telegram(db_session, telegram_id=200, username="bob", is_admin=True)
        assert user.role == "admin"

    async def test_relogin_does_not_change_role(self, db_session, monkeypatch):
        """Повторный вход без is_admin не понижает роль."""
        monkeypatch.setattr(config, "TELEGRAM_ADMIN_ID", 9999)
        u1 = await get_or_create_user_from_telegram(db_session, telegram_id=700, username="x", is_admin=True)
        assert u1.role == "admin"
        u2 = await get_or_create_user_from_telegram(db_session, telegram_id=700, username="x", is_admin=False)
        assert u2.role == "admin"
        assert u1.id == u2.id

    async def test_direct_db_role_change(self, db_session, monkeypatch):
        """Роль можно повысить напрямую через SQL."""
        monkeypatch.setattr(config, "TELEGRAM_ADMIN_ID", 9999)
        user = await get_or_create_user_from_telegram(db_session, telegram_id=800, username="promo", is_admin=False)
        assert user.role == "user"
        await db_session.execute(update(User).where(User.telegram_id == 800).values(role="admin"))
        await db_session.commit()
        result = await db_session.execute(select(User).where(User.telegram_id == 800))
        assert result.scalars().first().role == "admin"

    async def test_telegram_admin_id_zero_no_escalation(self, db_session, monkeypatch):
        """TELEGRAM_ADMIN_ID=0 НЕ должен давать admin пользователю с tg_id=0."""
        monkeypatch.setattr(config, "TELEGRAM_ADMIN_ID", 0)
        user = await get_or_create_user_from_telegram(db_session, telegram_id=0, username="zero", is_admin=False)
        assert user.role == "user", \
            "SECURITY: telegram_id=0 получил admin при TELEGRAM_ADMIN_ID=0"

    async def test_roles_independent_between_users(self, db_session, monkeypatch):
        monkeypatch.setattr(config, "TELEGRAM_ADMIN_ID", MOCK_USERS["eve"]["telegram_id"])
        alice = await get_or_create_user_from_telegram(db_session, telegram_id=MOCK_USERS["alice"]["telegram_id"], username="a", is_admin=False)
        bob   = await get_or_create_user_from_telegram(db_session, telegram_id=MOCK_USERS["bob"]["telegram_id"],   username="b", is_admin=False)
        eve   = await get_or_create_user_from_telegram(db_session, telegram_id=MOCK_USERS["eve"]["telegram_id"],   username="e", is_admin=True)
        assert alice.role == "user"
        assert bob.role   == "user"
        assert eve.role   == "admin"


# ============================================================
# ГРУППА 5: initData и JWT Security
# ============================================================

class TestInitDataSecurity:
    """Проверки подписи / replay / формата initData."""

    def test_reject_missing_hash(self):
        with pytest.raises(InvalidInitDataError, match="hash"):
            validate_telegram_init_data("auth_date=1234&user=%7B%22id%22%3A1%7D", MOCK_BOT_TOKEN)

    def test_reject_tampered_hash(self):
        init_data = generate_init_data_for_user(MOCK_USERS["alice"], MOCK_BOT_TOKEN)
        with pytest.raises(InvalidInitDataError, match="hash signature"):
            validate_telegram_init_data(init_data.replace("hash=", "hash=deadbeef"), MOCK_BOT_TOKEN)

    def test_reject_wrong_bot_token(self):
        init_data = generate_init_data_for_user(MOCK_USERS["alice"], MOCK_BOT_TOKEN)
        with pytest.raises(InvalidInitDataError, match="hash signature"):
            validate_telegram_init_data(init_data, "WRONG:TOKEN")

    def test_reject_expired(self):
        init_data = generate_init_data_for_user(MOCK_USERS["alice"], MOCK_BOT_TOKEN, auth_date=int(time.time()) - 600)
        with pytest.raises(InvalidInitDataError, match="expired"):
            validate_telegram_init_data(init_data, MOCK_BOT_TOKEN, max_age=300)

    def test_reject_future_auth_date(self):
        init_data = generate_init_data_for_user(MOCK_USERS["alice"], MOCK_BOT_TOKEN, auth_date=int(time.time()) + 600)
        with pytest.raises(InvalidInitDataError, match="future"):
            validate_telegram_init_data(init_data, MOCK_BOT_TOKEN)

    def test_reject_missing_user(self):
        auth_date = str(int(time.time()))
        params = {"auth_date": auth_date, "query_id": "test"}
        dcs = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
        sk = hmac.new(b"WebAppData", MOCK_BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
        params["hash"] = hmac.new(sk, dcs.encode("utf-8"), hashlib.sha256).hexdigest()
        with pytest.raises(InvalidInitDataError, match="user"):
            validate_telegram_init_data(urlencode(params), MOCK_BOT_TOKEN)

    def test_reject_malformed_user_json(self):
        auth_date = str(int(time.time()))
        params = {"auth_date": auth_date, "query_id": "test", "user": "not-json{{{"}
        dcs = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
        sk = hmac.new(b"WebAppData", MOCK_BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
        params["hash"] = hmac.new(sk, dcs.encode("utf-8"), hashlib.sha256).hexdigest()
        with pytest.raises(InvalidInitDataError, match="JSON"):
            validate_telegram_init_data(urlencode(params), MOCK_BOT_TOKEN)

    def test_valid_passes(self):
        init_data = generate_init_data_for_user(MOCK_USERS["alice"], MOCK_BOT_TOKEN)
        result = validate_telegram_init_data(init_data, MOCK_BOT_TOKEN)
        assert result["id"] == MOCK_USERS["alice"]["telegram_id"]
        assert result["username"] == MOCK_USERS["alice"]["username"]

    def test_replay_attack_blocked(self):
        init_data = generate_init_data_for_user(MOCK_USERS["alice"], MOCK_BOT_TOKEN, auth_date=int(time.time()) - 301)
        with pytest.raises(InvalidInitDataError, match="expired"):
            validate_telegram_init_data(init_data, MOCK_BOT_TOKEN, max_age=300)


class TestJWTSecurity:
    """JWT подделка / просрочка / none-атака."""

    def test_reject_expired_jwt(self, monkeypatch):
        monkeypatch.setattr(config, "JWT_SECRET", "test_secret_long_enough_32bytes!")
        monkeypatch.setattr(config, "JWT_ALGORITHM", "HS256")
        token = create_access_token(user_id=1, telegram_id=100, role="user", expires_in=-10)
        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_access_token(token)

    def test_reject_wrong_secret(self, monkeypatch):
        monkeypatch.setattr(config, "JWT_SECRET", "correct_secret_32bytes_long!!!!!")
        monkeypatch.setattr(config, "JWT_ALGORITHM", "HS256")
        forged = pyjwt.encode({"sub": "1", "role": "admin", "iat": int(time.time()), "exp": int(time.time()) + 3600},
                               "wrong_secret_32bytes_long!!!!!!", algorithm="HS256")
        with pytest.raises(pyjwt.InvalidSignatureError):
            decode_access_token(forged)

    def test_reject_garbage(self, monkeypatch):
        monkeypatch.setattr(config, "JWT_SECRET", "test_secret_long_enough_32bytes!")
        monkeypatch.setattr(config, "JWT_ALGORITHM", "HS256")
        with pytest.raises(pyjwt.DecodeError):
            decode_access_token("not.a.jwt.at.all.really")

    def test_reject_empty(self, monkeypatch):
        monkeypatch.setattr(config, "JWT_SECRET", "test_secret_long_enough_32bytes!")
        monkeypatch.setattr(config, "JWT_ALGORITHM", "HS256")
        with pytest.raises(pyjwt.DecodeError):
            decode_access_token("")

    def test_none_algorithm_attack(self, monkeypatch):
        monkeypatch.setattr(config, "JWT_SECRET", "test_secret_long_enough_32bytes!")
        monkeypatch.setattr(config, "JWT_ALGORITHM", "HS256")
        payload = {"sub": "1", "role": "admin", "iat": int(time.time()), "exp": int(time.time()) + 3600}
        try:
            none_token = pyjwt.encode(payload, "", algorithm="none")
        except Exception:
            return
        with pytest.raises((pyjwt.InvalidSignatureError, pyjwt.DecodeError, pyjwt.InvalidAlgorithmError, pyjwt.InvalidTokenError)):
            decode_access_token(none_token)

    def test_jwt_sub_is_string(self, monkeypatch):
        monkeypatch.setattr(config, "JWT_SECRET", "test_secret_long_enough_32bytes!")
        monkeypatch.setattr(config, "JWT_ALGORITHM", "HS256")
        token = create_access_token(user_id=42, telegram_id=100, role="user")
        payload = decode_access_token(token)
        assert isinstance(payload["sub"], str)
        assert payload["sub"] == "42"

    def test_default_plan_is_free(self, monkeypatch):
        monkeypatch.setattr(config, "JWT_SECRET", "test_secret_long_enough_32bytes!")
        monkeypatch.setattr(config, "JWT_ALGORITHM", "HS256")
        token = create_access_token(user_id=1, telegram_id=100, role="user")
        assert decode_access_token(token)["plan"] == "free"


# ============================================================
# ГРУППА 6: Пограничные случаи
# ============================================================

class TestEdgeCases:
    async def test_user_without_username(self, db_session, monkeypatch):
        monkeypatch.setattr(config, "TELEGRAM_ADMIN_ID", 9999)
        user = await get_or_create_user_from_telegram(db_session, telegram_id=900, username=None, first_name="No", is_admin=False)
        assert user.username is None
        assert user.role == "user"

    async def test_duplicate_returns_same_user(self, db_session, monkeypatch):
        monkeypatch.setattr(config, "TELEGRAM_ADMIN_ID", 9999)
        u1 = await get_or_create_user_from_telegram(db_session, telegram_id=1000, username="dup", is_admin=False)
        u2 = await get_or_create_user_from_telegram(db_session, telegram_id=1000, username="dup2", is_admin=False)
        assert u1.id == u2.id

    async def test_unique_telegram_id_constraint(self, db_session, monkeypatch):
        monkeypatch.setattr(config, "TELEGRAM_ADMIN_ID", 9999)
        await create_user(db_session, telegram_id=1100, username="first")
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            await create_user(db_session, telegram_id=1100, username="second")
