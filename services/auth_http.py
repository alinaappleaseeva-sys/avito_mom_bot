from aiohttp import web
import json
from config import config
from database.database import async_session
from database.crud import get_or_create_user_from_telegram
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from database.errors import DatabaseError
import asyncio
from utils.telegram_init_data import validate_telegram_init_data, InvalidInitDataError
from utils.jwt_tokens import create_access_token, decode_access_token
from utils.logger import setup_logger
import jwt

logger = setup_logger(__name__)

async def auth_telegram_handler(request: web.Request) -> web.Response:
    """
    Эндпоинт авторизации Telegram Mini App.
    Ожидает JSON вида: {"init_data": "<строка>"}
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)
        
    init_data = body.get("init_data")
    if not init_data:
        return web.json_response({"error": "Missing 'init_data' in payload"}, status=400)
        
    # Валидация подписи initData
    try:
        tg_user_data = validate_telegram_init_data(init_data, config.BOT_TOKEN)
    except InvalidInitDataError as e:
        logger.warning(f"Failed initData validation: {e}")
        return web.json_response({"error": "Unauthorized", "details": str(e)}, status=401)
        
    telegram_id = int(tg_user_data["id"])
    username = tg_user_data.get("username")
    first_name = tg_user_data.get("first_name")
    last_name = tg_user_data.get("last_name")

    try:
        async with async_session() as session:
            user = await get_or_create_user_from_telegram(
                session=session,
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                is_admin=(telegram_id == config.TELEGRAM_ADMIN_ID and config.TELEGRAM_ADMIN_ID != 0)
            )

            token = create_access_token(
                user_id=user.id,
                telegram_id=user.telegram_id,
                role=user.role
            )

            return web.json_response({
                "token": token,
                "user": {
                    "id": user.id,
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role
                }
            })
    except (SQLAlchemyError, OperationalError, DatabaseError, asyncio.TimeoutError) as e:
        logger.error(f"Database unavailable during auth: {e}")
        return web.json_response({"error": "Service Unavailable", "details": "DB unavailable or overloaded. Try again later."}, status=503)
    except Exception as e:
        logger.exception(f"Unexpected error during user authorization step: {e}")
        return web.json_response({"error": "Internal Server Error"}, status=500)

@web.middleware
async def jwt_auth_middleware(request: web.Request, handler) -> web.Response:
    """
    Middleware для проверки JWT токена в заголовке Authorization.
    Если маршрут требует авторизации, извлекает токен, валидирует
    и кладет полезную нагрузку в request['user'].
    """
    # Пропускаем открытые маршруты (например, саму авторизацию)
    if request.path == '/auth/telegram':
        return await handler(request)
        
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return web.json_response({"error": "Missing or invalid Authorization header"}, status=401)
        
    token = auth_header.split(" ")[1]
    
    try:
        payload = decode_access_token(token)
        request['user'] = payload
    except jwt.ExpiredSignatureError:
        return web.json_response({"error": "Token has expired"}, status=401)
    except jwt.InvalidTokenError:
        return web.json_response({"error": "Invalid token"}, status=401)
        
    return await handler(request)

def init_auth_app() -> web.Application:
    """
    Инициализирует aiohttp приложение авторизации.
    Способ запуска можно интегрировать с aiogram-диспетчером, 
    если проект будет работать с вебхуками, 
    или просто поднять на отдельном порту.
    """
    app = web.Application(middlewares=[jwt_auth_middleware])
    app.router.add_post('/auth/telegram', auth_telegram_handler)
    return app
