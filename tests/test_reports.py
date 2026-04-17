import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from services.reports import generate_weekly_report
from utils.constants import ItemStatus

@pytest.fixture
def mock_item():
    item = MagicMock()
    item.id = 1
    item.title = "Test Item"
    item.price = 1000
    item.status = ItemStatus.ACTIVE.value
    item.avito_item_id = "12345"
    item.views = 0
    item.contacts = 0
    item.created_at = datetime.now(timezone.utc) - timedelta(days=5) # Not fresh anymore
    return item

@pytest.mark.asyncio
async def test_generate_weekly_report_no_items():
    with patch("services.reports.get_user_items", return_value=[]) as mock_get_items:
        report = await generate_weekly_report(123)
        assert report is None
        
@pytest.mark.asyncio
async def test_generate_weekly_report_mock_mode(mock_item):
    with patch("services.reports.get_user_items", return_value=[mock_item]), \
         patch("services.reports.config") as mock_config, \
         patch("services.reports.avito_client") as mock_client, \
         patch("services.reports.update_item_sync") as mock_sync:
        
        mock_config.AVITO_API_MODE = "mock"
        mock_client.get_listing_stats.return_value = {"views": 100, "contacts": 5}
        
        report = await generate_weekly_report(123)
        
        assert "🟣 Режим эмуляции" in report
        assert "👁 Просмотры: 100 | 💬 Контакты: 5" in report
        assert "💡 <i>Рекомендация:</i> 🔥 Идут запросы!" in report
        mock_sync.assert_called_once_with(1, 123, views=100, contacts=5)

@pytest.mark.asyncio
async def test_generate_weekly_report_network_error(mock_item):
    from services.avito_client import AvitoAPIError
    mock_item.views = 50
    mock_item.contacts = 0
    
    with patch("services.reports.get_user_items", return_value=[mock_item]), \
         patch("services.reports.config") as mock_config, \
         patch("services.reports.avito_client") as mock_client:
        
        mock_config.AVITO_API_MODE = "production"
        mock_client.get_listing_stats.side_effect = AvitoAPIError("Network Err")
        
        report = await generate_weekly_report(123)
        
        assert "🟡 Кэш" in report
        assert "👁 Просмотры: 50 | 💬 Контакты: 0" in report
        assert "💡 <i>Рекомендация:</i> Просмотры есть, обращений нет" in report

@pytest.mark.asyncio
async def test_generate_weekly_report_fresh_item_zero_views(mock_item):
    mock_item.created_at = datetime.now(timezone.utc) - timedelta(hours=10) # fresh
    
    with patch("services.reports.get_user_items", return_value=[mock_item]), \
         patch("services.reports.config") as mock_config, \
         patch("services.reports.avito_client") as mock_client, \
         patch("services.reports.update_item_sync"):
        
        mock_config.AVITO_API_MODE = "production"
        mock_client.get_listing_stats.return_value = {"views": 0, "contacts": 0}
        
        report = await generate_weekly_report(123)
        
        assert "🟢 Актуально с Авито" in report
        assert "💡 <i>Рекомендация:</i> Объявление совсем свежее, статистика еще не собралась." in report
