import pytest
from unittest.mock import patch, MagicMock
from database.crud import get_item_by_id, delete_item
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
