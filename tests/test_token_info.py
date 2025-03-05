import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.token_info import detect_chain, get_token_info, format_token_info

@pytest.mark.parametrize("address, expected_chain", [
    ("EQAYpxYkdsiJoOxnBqhrx5XkEyUNbRk0oHDnMIaKHiWTcRRv", "ton"),
    ("So11111111111111111111111111111111111111112", "solana"),
])
def test_detect_chain_valid(address, expected_chain):
    """Test chain detection with valid addresses."""
    assert detect_chain(address) == expected_chain

@pytest.mark.parametrize("address", [
    "invalid",
    "ABC123",
])
def test_detect_chain_invalid(address):
    """Test chain detection with invalid addresses."""
    with pytest.raises(ValueError, match="Invalid or unsupported token address"):
        detect_chain(address)

@pytest.mark.asyncio
async def test_get_token_info_ton_success():
    mock_ton_info = {"symbol": "TON", "price_usd": 3.1196, "address": "EQAYpxYkdsiJoOxnBqhrx5XkEyUNbRk0oHDnMIaKHiWTcRRv"}
    with patch("services.token_info.detect_chain", return_value="ton"):
        with patch("blockchain.ton.token.get_ton_token_info", AsyncMock(return_value=mock_ton_info)):
            with patch("blockchain.ton.token.get_ton_price", AsyncMock(return_value=3.1196)):
                result = await get_token_info("EQAYpxYkdsiJoOxnBqhrx5XkEyUNbRk0oHDnMIaKHiWTcRRv")
                assert result == (mock_ton_info, 3.1196)

@pytest.mark.asyncio
async def test_get_token_info_solana_success():
    mock_sol_info = {"symbol": "SOL", "price_usd": 144.531411, "address": "So11111111111111111111111111111111111111112"}
    with patch("services.token_info.detect_chain", return_value="solana"):
        with patch("blockchain.solana.token.get_solana_token_info", AsyncMock(return_value=mock_sol_info)):
            with patch("blockchain.solana.token.get_sol_price", AsyncMock(return_value=144.531411)):
                result = await get_token_info("So11111111111111111111111111111111111111112")
                assert result == (mock_sol_info, 144.531411)


@pytest.mark.asyncio
async def test_get_token_info_invalid_chain():
    """Test token info fetch with invalid chain."""
    with patch("services.token_info.detect_chain", side_effect=ValueError("Invalid chain")):
        result = await get_token_info("invalid")
        assert result is None

@pytest.mark.asyncio
async def test_format_token_info_ton():
    """Test formatting TON token info."""
    token_info = {
        "symbol": "TON", "name": "Toncoin", "price_usd": 2.5, "liquidity": 1000000,
        "market_cap": 5000000000, "holders_count": 10000, "address": "EQ...",
        "mintable": False, "renounced": True, "social": ["https://t.me/ton"], "websites": ["https://ton.org"]
    }
    context = MagicMock()
    context.user_data = {"buy_amount": 0.5, "slippage": 5}
    formatted = await format_token_info(token_info, "ton", 10.0, 2.5, context)
    assert "TON - Toncoin" in formatted
    assert "Market Cap: $5000.00m" in formatted
    assert "Buy Amount: 0.5 TON" in formatted

@pytest.mark.asyncio
async def test_format_token_info_solana():
    """Test formatting Solana token info."""
    token_info = {
        "symbol": "SOL", "name": "Solana", "price_usd": 150.0, "liquidity": 500000,
        "market_cap": 1000000000, "holders_count": 5000, "address": "So...",
        "mintable": True, "renounced": False, "social": [], "websites": []
    }
    context = MagicMock()
    context.user_data = {"buy_amount": 0.05, "slippage": 50}
    formatted = await format_token_info(token_info, "solana", 1.0, 150.0, context)
    assert "SOL - Solana" in formatted
    assert "Market Cap: $1000.00m" in formatted
    assert "Buy Amount: 0.05 SOL" in formatted