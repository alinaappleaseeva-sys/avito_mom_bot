import hmac
import hashlib
import json
import time
from urllib.parse import parse_qsl

class InvalidInitDataError(Exception):
    """Exception raised when Telegram init data is invalid or expired."""
    pass

def validate_telegram_init_data(init_data: str, bot_token: str, max_age: int = 300) -> dict:
    """
    Validates data received via the Telegram Mini App (initData).
    According to the official Telegram specification:
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    
    Args:
        init_data: The raw query string received from WebApp (Telegram.WebApp.initData).
        bot_token: The secret bot token.
        max_age: Maximum allowed age of auth_date in seconds (default 300).
        
    Returns:
        dict: A dictionary containing extracted user fields: 
              'id', 'username', 'first_name', 'last_name'.
              
    Raises:
        InvalidInitDataError: If hash is false, data is expired or payload is malformed.
    """
    parsed_data = dict(parse_qsl(init_data))
    
    if "hash" not in parsed_data:
        raise InvalidInitDataError("Missing 'hash' in init data.")
        
    hash_val = parsed_data.pop("hash")
    
    # Check auth_date for expiration
    auth_date = parsed_data.get("auth_date")
    if auth_date:
        try:
            auth_timestamp = int(auth_date)
            # if the payload is older than max_age it is invalid (to prevent replay attacks)
            if time.time() - auth_timestamp > max_age:
                raise InvalidInitDataError("Init data is expired.")
        except ValueError:
            raise InvalidInitDataError("Invalid 'auth_date' format.")
            
    # Sort remaining pairs alphabetically by key and build data_check_string
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed_data.items())
    )
    
    # Calculate secret key using WebAppData constant and the bot token
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    
    # Calculate hash signature
    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(calculated_hash, hash_val):
        raise InvalidInitDataError("Invalid hash signature.")
        
    # Validation successful, now extract user payload
    if "user" not in parsed_data:
        raise InvalidInitDataError("Missing 'user' payload in init data.")
        
    try:
        user_data = json.loads(parsed_data["user"])
        return {
            "id": user_data.get("id"),
            "username": user_data.get("username"),
            "first_name": user_data.get("first_name"),
            "last_name": user_data.get("last_name")
        }
    except json.JSONDecodeError:
        raise InvalidInitDataError("Invalid 'user' JSON format.")
