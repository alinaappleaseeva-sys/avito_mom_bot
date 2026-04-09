import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from aiogram.types import Message, User
from utils.middlewares import RateLimitMiddleware

@pytest.mark.asyncio
async def test_rate_limit_middleware_allows_first_request():
    middleware = RateLimitMiddleware(limit_seconds=1)
    
    mock_handler = AsyncMock(return_value="success")
    mock_message = MagicMock(spec=Message)
    mock_message.from_user = MagicMock(spec=User)
    mock_message.from_user.id = 12345
    mock_data = {}

    result = await middleware(mock_handler, mock_message, mock_data)
    
    assert result == "success"
    mock_handler.assert_called_once_with(mock_message, mock_data)

@pytest.mark.asyncio
async def test_rate_limit_middleware_blocks_fast_requests():
    middleware = RateLimitMiddleware(limit_seconds=2)
    
    # Mocking asyncio.get_event_loop().time()
    with pytest.MonkeyPatch.context() as m:
        m.setattr(asyncio.get_event_loop(), "time", lambda: 100.0)
        
        mock_handler = AsyncMock(return_value="success")
        mock_message = AsyncMock(spec=Message)
        mock_message.from_user = MagicMock(spec=User)
        mock_message.from_user.id = 12345
        
        # First request at time = 100.0
        await middleware(mock_handler, mock_message, {})
        assert mock_handler.call_count == 1
        
        # Second request at time = 101.0 (blocked)
        m.setattr(asyncio.get_event_loop(), "time", lambda: 101.0)
        result = await middleware(mock_handler, mock_message, {})
        
        assert result is None
        assert mock_handler.call_count == 1 # Handler not called again
        mock_message.answer.assert_called_once() # User got warning
        
        # Third request at time = 103.0 (allowed)
        m.setattr(asyncio.get_event_loop(), "time", lambda: 103.0)
        await middleware(mock_handler, mock_message, {})
        assert mock_handler.call_count == 2

@pytest.mark.asyncio
async def test_rate_limit_middleware_ttl_cleanup():
    middleware = RateLimitMiddleware(limit_seconds=1, ttl_seconds=5)
    
    with pytest.MonkeyPatch.context() as m:
        # Time 100: User A makes request
        m.setattr(asyncio.get_event_loop(), "time", lambda: 100.0)
        mock_message_A = MagicMock(spec=Message)
        mock_message_A.from_user.id = 1
        await middleware(AsyncMock(), mock_message_A, {})
        
        assert 1 in middleware.user_timestamps
        
        # Time 106: User B makes request, triggers TTL cleanup
        m.setattr(asyncio.get_event_loop(), "time", lambda: 106.0)
        mock_message_B = MagicMock(spec=Message)
        mock_message_B.from_user.id = 2
        await middleware(AsyncMock(), mock_message_B, {})
        
        assert 2 in middleware.user_timestamps
        assert 1 not in middleware.user_timestamps # User A was cleaned up
