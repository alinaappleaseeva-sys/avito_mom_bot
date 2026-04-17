import jwt
import time
from config import config

def create_access_token(user_id: int, telegram_id: int, role: str, plan: str = "free", expires_in: int = 3600) -> str:
    """
    Создает JWT токен для авторизованного пользователя.
    
    Args:
        user_id: внутренний ID пользователя в БД.
        telegram_id: идентификатор в Telegram.
        role: роль (user, admin).
        plan: подписка (по умолчанию free).
        expires_in: время жизни токена в секундах (по умолчанию 1 час).
        
    Returns:
        Сгенерированная строка JWT токена.
    """
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "telegram_id": telegram_id,
        "role": role,
        "plan": plan,
        "iat": now,
        "exp": now + expires_in
    }
    
    token = jwt.encode(
        payload, 
        config.JWT_SECRET, 
        algorithm=config.JWT_ALGORITHM
    )
    return token

def decode_access_token(token: str) -> dict:
    """
    Расшифровывает JWT токен и проверяет срок его действия.
    
    Args:
        token: JWT строка.
        
    Returns:
        dict: полезная нагрузка.
        
    Raises:
        jwt.ExpiredSignatureError: Если токен просрочен.
        jwt.InvalidTokenError: Если токен невалиден.
    """
    payload = jwt.decode(
        token, 
        config.JWT_SECRET, 
        algorithms=[config.JWT_ALGORITHM]
    )
    return payload
