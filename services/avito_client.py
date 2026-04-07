import aiohttp
import time
from config import config
from utils.logger import setup_logger

logger = setup_logger(__name__)

class AvitoAPIError(Exception):
    """Exception raised for Avito API errors."""
    pass

class AvitoClient:
    def __init__(self):
        self.auth_url = "https://api.avito.ru/token/"
        self.client_id = config.AVITO_CLIENT_ID
        self.client_secret = config.AVITO_CLIENT_SECRET
        self.user_id = config.AVITO_USER_ID
        self._access_token = None
        self._token_expires_at = 0

    async def _get_access_token(self) -> str:
        if not self.client_id or not self.client_secret:
            raise AvitoAPIError("Avito credentials not configured")

        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        logger.info("Requesting new Avito access token...")
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.auth_url, data=data) as response:
                    res_data = await response.json()
                    
                    if response.status != 200:
                        logger.error(f"Avito Auth failed: {res_data}")
                        raise AvitoAPIError(f"Auth failed: {res_data.get('error_description', 'Unknown error')}")
                    
                    self._access_token = res_data.get("access_token")
                    expires_in = res_data.get("expires_in", 3600)
                    self._token_expires_at = time.time() + expires_in - 300 # Buffer
                    return self._access_token
            except aiohttp.ClientError as e:
                logger.error(f"Avito Auth Network error: {e}")
                raise AvitoAPIError(f"Network error during authorization: {e}")

    async def create_listing(self, item_data: dict) -> str:
        """
        Отправляет POST-запрос на создание объявления к Avito API.
        Возвращает: avito_item_id (string).
        """
        token = await self._get_access_token()
        url = f"https://api.avito.ru/core/v1/accounts/{self.user_id}/items"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Mock payload transformation, using Moscow as default Fallback
        payload = {
            "title": item_data.get("title", ""),
            "description": item_data.get("description", ""),
            "price": item_data.get("price", 0),
            "address": "Москва", 
            # and other required Avito fields placeholder...
        }

        async with aiohttp.ClientSession() as session:
            try:
                # В MVP мы имитируем 403 Forbidden, если ID пользователя не бизнес.
                # Поэтому мы готовы к gracefully handling error response.
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status in (401, 403):
                        logger.warning(f"Avito API access denied: {response.status}")
                        raise AvitoAPIError("У вашего профиля нет прав на автоматическую публикацию.")
                    
                    if response.status != 200:
                        logger.warning(f"Avito API item creation failed: {await response.text()}")
                        raise AvitoAPIError("Не удалось создать объявление на Авито.")

                    data = await response.json()
                    # В реальном API возвращается ID
                    return str(data.get("item_id", "test_id_123"))
            except aiohttp.ClientError as e:
                logger.error(f"Avito Create Item Network error: {e}")
                raise AvitoAPIError(f"Сетевая ошибка при создании: {e}")

    async def get_listing_stats(self, avito_item_id: str) -> dict:
        """
        Получает статистику просмотров и контактов.
        """
        token = await self._get_access_token()
        # Этот URL схематичный, для получения воронки.
        url = f"https://api.avito.ru/stats/v1/accounts/{self.user_id}/items/{avito_item_id}"
        
        headers = {
            "Authorization": f"Bearer {token}",
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "views": data.get("stats", {}).get("views", 0),
                            "contacts": data.get("stats", {}).get("contacts", 0)
                        }
                    else:
                        logger.warning(f"Failed to get stats: {response.status}")
                        return {"views": "N/A", "contacts": "N/A"}
            except aiohttp.ClientError as e:
                return {"views": "N/A", "contacts": "N/A"}

avito_client = AvitoClient()
