import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from database.crud import get_item_by_id, delete_item, delete_user_account
from database.errors import DatabaseError
from sqlalchemy.exc import SQLAlchemyError

@pytest.mark.asyncio
async def test_get_item_not_found():
    # Test behaviour when item doesn't exist
    item = await get_item_by_id(99999, 123456)
    assert item is None

@pytest.mark.asyncio
@patch('database.crud.async_session')
async def test_database_error_propagation(mock_session):
    # Setup mock to raise SQLAlchemyError
    mock_session_context = MagicMock()
    mock_session.return_value = mock_session_context
    mock_session_context.__aenter__.side_effect = SQLAlchemyError("Connection reset")

    # Verify that the DB helper raises DatabaseError instead of SQLAlchemyError
    with pytest.raises(DatabaseError) as exc_info:
        await delete_item(1, 123456)
    assert "Failed to delete item" in str(exc_info.value)

@pytest.mark.asyncio
@patch('database.crud.async_session')
async def test_delete_user_account(mock_session):
    mock_session_context = AsyncMock()
    mock_session.return_value = mock_session_context
    
    # Mocking rows returned to simulate successful deletion
    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_session_context.__aenter__.return_value.execute.return_value = mock_result
    
    result = await delete_user_account(123456)
    
    assert result is True
    # Verify execute was called twice (Items then User)
    assert mock_session_context.__aenter__.return_value.execute.call_count == 2
    mock_session_context.__aenter__.return_value.commit.assert_called_once()
