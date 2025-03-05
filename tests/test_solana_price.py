import pytest
from unittest.mock import AsyncMock, patch
from blockchain.solana.token import get_sol_price

@pytest.mark.asyncio
async def test_get_sol_price_success():
    """Test successful SOL price fetch."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"solana": {"usd": 144.531411}})

    with patch("aiohttp.ClientSession.get", return_value=mock_response):
        price = await get_sol_price(AsyncMock())
        assert price == 144.531411  # Match actual value from logs

@pytest.mark.asyncio
async def test_get_sol_price_api_failure():
    """Test SOL price fetch with API failure."""
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value="Server Error")

    with patch("aiohttp.ClientSession.get", return_value=mock_response):
        price = await get_sol_price(AsyncMock())
        assert price == 0.0  # Assuming fallback