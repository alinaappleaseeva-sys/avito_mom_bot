from aiohttp import web
import json
from config import config
from database.database import async_session
from database.crud import get_or_create_user_from_telegram, get_item_by_id
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from database.errors import DatabaseError
import asyncio
from utils.telegram_init_data import validate_telegram_init_data, InvalidInitDataError
from utils.jwt_tokens import create_access_token, decode_access_token
from utils.logger import setup_logger
import jwt

logger = setup_logger(__name__)

def build_error_response(code: str, message: str, status: int) -> web.Response:
    """Утилита для стандартизированного отформатированного ответа на ошибки API."""
    return web.json_response({
        "error": {
            "code": code,
            "message": message
        }
    }, status=status)

async def auth_telegram_handler(request: web.Request) -> web.Response:
    """
    Эндпоинт авторизации Telegram Mini App.
    Ожидает JSON вида: {"init_data": "<строка>"}
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return build_error_response("BAD_REQUEST", "Invalid JSON body", 400)
        
    init_data = body.get("init_data")
    if not init_data:
        return build_error_response("BAD_REQUEST", "Missing 'init_data' in payload", 400)
        
    # Валидация подписи initData
    try:
        tg_user_data = validate_telegram_init_data(init_data, config.BOT_TOKEN)
    except InvalidInitDataError as e:
        logger.warning(f"Failed initData validation: {e}")
        return build_error_response("UNAUTHORIZED", f"Unauthorized: {str(e)}", 401)
        
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
    except asyncio.TimeoutError as e:
        logger.error(f"Timeout during auth DB step: {e}")
        return build_error_response("GATEWAY_TIMEOUT", "Database timeout elapsed", 504)
    except (SQLAlchemyError, OperationalError, DatabaseError) as e:
        logger.error(f"Database unavailable during auth: {e}")
        return build_error_response("SERVICE_UNAVAILABLE", "Database unavailable or overloaded", 503)
    except Exception as e:
        logger.exception(f"Unexpected error during user authorization step: {e}")
        return build_error_response("INTERNAL_SERVER_ERROR", "Internal Server Error", 500)

async def get_item_handler(request: web.Request) -> web.Response:
    """
    Эндпоинт для получения предмета по ID.
    Проверяет, что предмет принадлежит авторизованному пользователю.
    Возвращает 403, если предмет принадлежит другому пользователю.
    """
    user_payload = request.get('user', {})
    telegram_id = user_payload.get('telegram_id')
    if not telegram_id:
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        item_id = int(request.match_info['item_id'])
    except (ValueError, KeyError):
        return web.json_response({"error": "Invalid item ID"}, status=400)

    try:
        async with async_session() as session:
            item = await get_item_by_id(item_id=item_id, user_id=telegram_id)
            if item is None:
                # Предмет не найден ИЛИ принадлежит другому пользователю.
                # Возвращаем 403, чтобы не раскрывать существование чужих предметов.
                return web.json_response(
                    {"error": "Forbidden", "details": "You do not have access to this item."},
                    status=403
                )

            return web.json_response({
                "item": {
                    "id": item.id,
                    "title": item.title,
                    "category": item.category,
                    "description": item.description,
                    "price": item.price,
                    "status": item.status,
                    "avito_url": item.avito_url,
                }
            })
    except Exception as e:
        logger.exception(f"Error fetching item {item_id}: {e}")
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
        return build_error_response("UNAUTHORIZED", "Missing or invalid Authorization header", 401)
        
    token = auth_header.split(" ")[1]
    
    try:
        payload = decode_access_token(token)
        request['user'] = payload
    except jwt.ExpiredSignatureError:
        return build_error_response("UNAUTHORIZED", "Token has expired", 401)
    except jwt.InvalidTokenError:
        return build_error_response("UNAUTHORIZED", "Invalid token signature", 401)
        
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
    app.router.add_get('/api/items/{item_id}', get_item_handler)
    return app
