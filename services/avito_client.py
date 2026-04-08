import aiohttp
import asyncio
import time
from typing import Optional, Dict, Any

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
        self.api_mode = config.AVITO_API_MODE
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self) -> None:
        timeout = aiohttp.ClientTimeout(total=15)
        self.session = aiohttp.ClientSession(timeout=timeout)
        logger.info(f"AvitoClient initialized in '{self.api_mode}' mode.")

    async def close(self) -> None:
        if self.session:
            await self.session.close()

    async def _get_access_token(self) -> str:
        """
        Получение временного токена (OAuth2 client_credentials).
        Docs: https://developers.avito.ru/api-catalog/auth/documentation
        """
        if self.api_mode == "mock":
            return "mock_token_123"

        if not self.client_id or not self.client_secret:
            raise AvitoAPIError("Avito credentials not configured in environment.")

        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        logger.info("Requesting new Avito access token...")
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        if not self.session:
            raise RuntimeError("AvitoClient session is not initialized")

        try:
            async with self.session.post(
                self.auth_url, 
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            ) as response:
                
                if response.status >= 500:
                    text_resp = await response.text()
                    logger.error(f"Avito Auth 5xx Server Error: {text_resp}")
                    raise AvitoAPIError("Avito server side error (5xx).")

                try:
                    res_data = await response.json()
                except ValueError:
                    text_resp = await response.text()
                    logger.error(f"Avito Auth Invalid JSON response: {text_resp}")
                    raise AvitoAPIError("Avito Auth response was not a valid JSON.")
                
                if response.status >= 400:
                    logger.error(f"Avito Auth 4xx Error: {res_data}")
                    raise AvitoAPIError(f"Auth failed: {res_data.get('error', 'unknown')} - {res_data.get('error_description', 'No description')}")
                
                self._access_token = res_data.get("access_token")
                expires_in = int(res_data.get("expires_in", 3600))
                self._token_expires_at = time.time() + expires_in - 300 # Buffer margin 5 mins
                
                if not self._access_token:
                    raise AvitoAPIError("Tokens is missing in 200 OK response")
                    
                return self._access_token
        except aiohttp.ClientError as e:
            logger.error(f"Avito Auth Network error: {e}")
            raise AvitoAPIError(f"Network error during authorization: {e}")

    async def create_listing(self, item_data: dict) -> str:
        """
        Отправляет POST-запрос на создание объявления к Avito API.
        
        ПОЛУ-МОК: В реальном режиме используется настоящий URL, но 
        передаваемая структура `payload` сильно схематична. 
        Для боевого продакшена необходимо сверяться с 
        https://developers.avito.ru/api-catalog/ (CPA / Autoload).
        """
        if self.api_mode == "mock":
            logger.info("MOCK MODE: Смуляция создания объявления.")
            await asyncio.sleep(1) # Имитация сетевой задержки
            return f"mock_item_{int(time.time())}"

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

        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status in (401, 403):
                    logger.warning(f"Avito API access denied: {response.status}")
                    raise AvitoAPIError("У вашего профиля нет прав на автоматическую публикацию.")
                
                if response.status != 200:
                    logger.warning(f"Avito API item creation failed: {await response.text()}")
                    raise AvitoAPIError("Не удалось создать объявление на Авито.")

                data = await response.json()
                return str(data.get("item_id", "test_id_123"))
        except aiohttp.ClientError as e:
            logger.error(f"Avito Create Item Network error: {e}")
            raise AvitoAPIError(f"Сетевая ошибка при создании: {e}")

    async def get_listing_stats(self, avito_item_id: str) -> Dict[str, Any]:
        """
        Получает сводную статистику по одному объявлению за последние 30 дней.
        Docs: https://developers.avito.ru/api-catalog
        """
        if self.api_mode == "mock":
            await asyncio.sleep(0.5)
            # Если передали "mock" id
            return {"views": 15, "contacts": 2}

        if not self.session:
            raise RuntimeError("AvitoClient session is not initialized")

        token = await self._get_access_token()
        url = f"https://api.avito.ru/stats/v1/accounts/{self.user_id}/items"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        import datetime
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=30)
        
        # Avito API docs list itemId as integer in stats request
        try:
            item_id_num = int(avito_item_id)
        except ValueError:
            logger.error(f"Avito item id '{avito_item_id}' must be numeric.")
            return {"views": "N/A", "contacts": "N/A"}
            
        payload = {
            "dateFrom": start_date.strftime("%Y-%m-%d"),
            "dateTo": end_date.strftime("%Y-%m-%d"),
            "fields": ["views", "contacts"],
            "itemIds": [item_id_num]
        }
        
        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status >= 500:
                    logger.error(f"Avito Stats 5xx Error: {await response.text()}")
                    return {"views": "N/A", "contacts": "N/A"}
                
                try:
                    data = await response.json()
                except ValueError:
                    logger.error(f"Avito Stats Invalid JSON: {await response.text()}")
                    return {"views": "N/A", "contacts": "N/A"}
                    
                if response.status >= 400:
                    logger.warning(f"Failed to get stats (HTTP {response.status}): {data}")
                    return {"views": "N/A", "contacts": "N/A"}
                
                # Extracting using standard Avito schema
                items_data = data.get("result", {}).get("items", [])
                if not items_data:
                    return {"views": 0, "contacts": 0}
                    
                item_stats = items_data[0].get("stats", [])
                total_views = sum(day_stat.get("views", 0) for day_stat in item_stats)
                total_contacts = sum(day_stat.get("contacts", 0) for day_stat in item_stats)
                
                return {"views": total_views, "contacts": total_contacts}
        except aiohttp.ClientError as e:
            logger.error(f"Avito Stats network error: {e}")
            return {"views": "N/A", "contacts": "N/A"}
        except Exception as e:
            logger.error(f"Avito Stats unexpected error: {e}")
            return {"views": "N/A", "contacts": "N/A"}

avito_client = AvitoClient()
