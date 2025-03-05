import pytest
from unittest.mock import AsyncMock, patch
from blockchain.ton.token import get_ton_price

@pytest.mark.asyncio
async def test_get_ton_price_success():
    """Test successful TON price fetch."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"rates": {"TON": {"price": 3.1196}}})

    with patch("aiohttp.ClientSession.get", return_value=mock_response):
        price = await get_ton_price(AsyncMock())
        assert price == 3.1196  # Match actual behavior from your logs

@pytest.mark.asyncio
async def test_get_ton_price_api_failure():
    """Test TON price fetch with API failure."""
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.text = AsyncMock(return_value="Bad Request")

    with patch("aiohttp.ClientSession.get", return_value=mock_response):
        price = await get_ton_price(AsyncMock())
        assert price == 0.0  # Assuming fallback to 0.0