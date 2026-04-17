import aiohttp
import asyncio
import time
from typing import Optional, Dict, Any

from config import config
from utils.logger import setup_logger
from database.models import Item
from services.avito_mapper import build_avito_payload_for_item

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
                    logger.debug(f"Avito Auth 5xx Server Error body: {text_resp}")
                    logger.error(f"Avito Auth 5xx Server Error (HTTP {response.status}).")
                    raise AvitoAPIError("Avito server side error (5xx).")

                try:
                    res_data = await response.json()
                except ValueError:
                    text_resp = await response.text()
                    logger.debug(f"Avito Auth Invalid JSON body: {text_resp}")
                    logger.error("Avito Auth response was not a valid JSON.")
                    raise AvitoAPIError("Avito Auth response was not a valid JSON.")
                
                if response.status >= 400:
                    logger.debug(f"Avito Auth 4xx Error body: {res_data}")
                    logger.warning(f"Avito Auth failed with HTTP {response.status}.")
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

    async def create_listing(self, item: Item) -> str:
        """
        Создание (размещение) объявления через REST API (CРА-модель).
        Docs: https://developers.avito.ru/api-catalog
        """
        if self.api_mode == "mock":
            logger.info("MOCK MODE: Симуляция создания объявления.")
            await asyncio.sleep(1) # Имитация сетевой задержки
            return f"mock_item_{int(time.time())}"

        if not self.session:
            raise RuntimeError("AvitoClient session is not initialized")

        token = await self._get_access_token()
        
        # Базовый REST метод для создания единичного объявления (Обычно это Autoload или CPA).
        url = f"https://api.avito.ru/core/v1/accounts/{self.user_id}/items"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Используем маппер для формирования payload
        payload = build_avito_payload_for_item(item)

        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status >= 500:
                    text_resp = await response.text()
                    logger.debug(f"Avito Create Item 5xx Error body: {text_resp}")
                    logger.error(f"Avito Create Item 5xx Error (HTTP {response.status}).")
                    raise AvitoAPIError("Avito server side error (5xx) while creating listing.")
                    
                try:
                    data = await response.json()
                except ValueError:
                    text_resp = await response.text()
                    logger.debug(f"Avito Create Item Invalid JSON body: {text_resp}")
                    logger.error("Avito Create Item response was not a valid JSON.")
                    raise AvitoAPIError("Avito Create Item response was not a valid JSON.")

                if response.status == 400:
                    logger.debug(f"Avito API Bad Request body: {data}")
                    logger.warning("Avito API Bad Request (400 validation error).")
                    raise AvitoAPIError(f"Ошибка валидации данных объявления: {data.get('error', {}).get('message', 'Unknown bad request')}")
                    
                if response.status in (401, 403):
                    logger.debug(f"Avito API access denied body: {data}")
                    logger.warning(f"Avito API access denied (HTTP {response.status}).")
                    raise AvitoAPIError("У вашего профиля или сервисного приложения нет прав на автоматическую публикацию (403 Forbidden).")
                
                if response.status >= 400:
                    logger.debug(f"Avito API creation failed body: {data}")
                    logger.warning(f"Avito API creation failed (HTTP {response.status}).")
                    raise AvitoAPIError("Не удалось создать объявление на Авито.")

                item_id = data.get("itemId") or data.get("id")
                if not item_id:
                    logger.debug(f"Avito Create Item response without ID: {data}")
                    raise AvitoAPIError("Avito API response did not contain an item ID.")
                return str(item_id)
                
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
            logger.error(f"Avito item id '{avito_item_id}' must be numeric for stats.")
            raise AvitoAPIError(f"Invalid non-numeric Avito item ID: {avito_item_id}")
            
        payload = {
            "dateFrom": start_date.strftime("%Y-%m-%d"),
            "dateTo": end_date.strftime("%Y-%m-%d"),
            "fields": ["views", "contacts"],
            "itemIds": [item_id_num]
        }
        
        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status >= 500:
                    text_resp = await response.text()
                    logger.debug(f"Avito Stats 5xx Error body: {text_resp}")
                    logger.error(f"Avito Stats 5xx Error (HTTP {response.status}).")
                    raise AvitoAPIError("Avito API 5xx error while getting stats.")
                
                try:
                    data = await response.json()
                except ValueError:
                    text_resp = await response.text()
                    logger.debug(f"Avito Stats Invalid JSON body: {text_resp}")
                    logger.error("Avito Stats Invalid JSON response.")
                    raise AvitoAPIError("Avito API returned invalid JSON for stats.")
                    
                if response.status >= 400:
                    logger.debug(f"Failed to get stats body: {data}")
                    logger.warning(f"Failed to get stats (HTTP {response.status}).")
                    raise AvitoAPIError(f"Avito API error {response.status} while getting stats.")
                
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
            raise AvitoAPIError(f"Network error while getting stats: {e}")

    async def get_item_info(self, avito_item_id: str) -> Dict[str, Any]:
        """
        Получает подробную информацию об объявлении (статус, причина отклонения).
        Docs: https://developers.avito.ru/api-catalog/item/documentation
        """
        if self.api_mode == "mock":
            await asyncio.sleep(0.5)
            # Мок разных статусов по паттернам в ID для тестирования
            if "reject" in str(avito_item_id):
                return {"status": "rejected", "reject_reason": "Заглушка: фото низкого качества или товар запрещен к продаже"}
            if "moderat" in str(avito_item_id):
                return {"status": "in_moderation"}
            return {"status": "active"}

        if not self.session:
            raise RuntimeError("AvitoClient session is not initialized")

        token = await self._get_access_token()
        url = f"https://api.avito.ru/core/v1/accounts/{self.user_id}/items/{avito_item_id}"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status >= 500:
                    text_resp = await response.text()
                    logger.error(f"Avito get_item_info 5xx Error (HTTP {response.status}): {text_resp}")
                    raise AvitoAPIError("Avito API 5xx error while getting item info.")
                
                try:
                    data = await response.json()
                except ValueError:
                    logger.error("Avito get_item_info Invalid JSON response.")
                    raise AvitoAPIError("Avito API returned invalid JSON for item info.")
                    
                if response.status >= 400:
                    logger.warning(f"Failed to get item info (HTTP {response.status}): {data}")
                    raise AvitoAPIError(f"Avito API error {response.status} while getting item info.")
                
                return data
        except aiohttp.ClientError as e:
            logger.error(f"Avito get_item_info network error: {e}")
            raise AvitoAPIError(f"Network error while getting item info: {e}")

avito_client = AvitoClient()
