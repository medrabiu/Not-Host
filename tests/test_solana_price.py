import pytest
import aiohttp
import asyncio
from unittest.mock import AsyncMock, patch
from blockchain.solana.token import get_solana_token_info  # Replace 'your_module' with the actual module name

@pytest.mark.asyncio
@pytest.mark.skip(reason="Skiping due to different sources")
async def test_get_solana_token_info_success():
    token_address = "TOKEN1234567890TOKEN1234567890TOKEN12"
    
    mock_dex_response = {
        "pairs": [{
            "chainId": "solana",
            "baseToken": {"name": "MockToken", "symbol": "MTK"},
            "priceUsd": "0.5",
            "liquidity": {"usd": 10000},
            "marketCap": 500000,
            "info": {"imageUrl": "https://example.com/token.png", "socials": [], "websites": []}
        }]
    }
    
    with patch("aiohttp.ClientSession.get", new_callable=AsyncMock) as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = mock_dex_response
        mock_get.return_value.__aenter__.return_value = mock_resp

        token_info = await get_solana_token_info(token_address)

        assert token_info is not None
        assert token_info["name"] == "MockToken"
        assert token_info["symbol"] == "MTK"
        assert token_info["price_usd"] == 0.5
        assert token_info["liquidity"] == 10000
        assert token_info["market_cap"] == 500000

@pytest.mark.asyncio
async def test_get_solana_token_info_invalid_address():
    invalid_address = "INVALID123"
    token_info = await get_solana_token_info(invalid_address)
    assert token_info is None

@pytest.mark.asyncio
async def test_get_solana_token_info_dexscreener_failure():
    token_address = "TOKEN1234567890TOKEN1234567890TOKEN12"
    
    with patch("aiohttp.ClientSession.get", new_callable=AsyncMock) as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 500  # Simulating API failure
        mock_resp.json.return_value = {}
        mock_get.return_value.__aenter__.return_value = mock_resp

        token_info = await get_solana_token_info(token_address)

        assert token_info is None  # Since all fallbacks fail

@pytest.mark.asyncio
async def test_get_solana_token_info_retries_on_timeout():
    token_address = "TOKEN1234567890TOKEN1234567890TOKEN12"
    
    with patch("aiohttp.ClientSession.get", new_callable=AsyncMock) as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.side_effect = asyncio.TimeoutError  # Simulate a timeout
        mock_get.return_value.__aenter__.return_value = mock_resp

        token_info = await get_solana_token_info(token_address)

        assert token_info is None  # Expect None since retries should fail