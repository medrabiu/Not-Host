import pytest
import aiohttp
import base58
from unittest.mock import AsyncMock, patch, MagicMock
from solders.keypair import Keypair
from blockchain.solana.trade import execute_solana_swap
from services.crypto import CIPHER

class MockSolanaWallet:
    def __init__(self):
        self.public_key = "3rXbD6fQ8QXN8e5gX5v8T5Z5W8K9J2X8Y5V8T5Z5W8K9J2X8Y5V8T5Z"
        self.encrypted_private_key = "mock_encrypted_key"  # Match actual type

@pytest.mark.asyncio
async def test_execute_solana_swap_success():
    mock_wallet = MockSolanaWallet()
    mock_keypair = Keypair()
    mock_tx_data = base58.b58encode(b"mock_transaction_data")  # Ensure valid length
    with patch.object(CIPHER, "decrypt", return_value=bytes(mock_keypair.secret()[:32])):
        with patch("solders.keypair.Keypair.from_seed", return_value=mock_keypair):
            mock_quote_response = {"outAmount": "1000000000", "inAmount": "50000000"}
            mock_swap_response = {"swapTransaction": mock_tx_data.decode('ascii')}
            mock_tx = MagicMock()
            mock_tx_id = "mock_tx_id"

            async def mock_get(*args, **kwargs):
                response = AsyncMock()
                response.status = 200
                response.json = AsyncMock(return_value=mock_quote_response)
                return response

            async def mock_post(*args, **kwargs):
                response = AsyncMock()
                response.status = 200
                response.json = AsyncMock(return_value=mock_swap_response)
                return response

            with patch("aiohttp.ClientSession.get", mock_get):
                with patch("aiohttp.ClientSession.post", mock_post):
                    with patch("solders.transaction.VersionedTransaction.from_bytes", return_value=mock_tx):
                        with patch("solana.rpc.async_api.AsyncClient.send_transaction", AsyncMock(return_value=mock_tx_id)):
                            result = await execute_solana_swap(mock_wallet, "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", 0.05, 50)
                            assert result["output_amount"] == 1000000000
                            assert result["tx_id"] == "mock_tx_id"

@pytest.mark.asyncio
async def test_execute_solana_swap_invalid_amount():
    """Test swap with invalid SOL amount."""
    mock_wallet = MockSolanaWallet()
    with pytest.raises(ValueError, match="Amount to swap must be a positive number"):
        await execute_solana_swap(mock_wallet, "EPjFW...", -0.05, 50)


@pytest.mark.asyncio
async def test_execute_solana_swap_invalid_slippage():
    """Test swap with invalid slippage."""
    mock_wallet = MockSolanaWallet()
    with pytest.raises(ValueError, match="Slippage must be between 0 and 10000 basis points"):
        await execute_solana_swap(mock_wallet, "EPjFW...", 0.05, -50)


@pytest.mark.asyncio
async def test_execute_solana_swap_api_failure():
    """Test swap with Jupiter API failure."""
    mock_wallet = MockSolanaWallet()
    with patch.object(CIPHER, "decrypt", return_value=bytes(Keypair().secret()[:32])):
        with patch("solders.keypair.Keypair.from_seed", return_value=Keypair()):
            async def mock_get(*args, **kwargs):
                response = AsyncMock()
                response.status = 400
                response.text = AsyncMock(return_value="Bad Request")
                return response

            with patch("aiohttp.ClientSession.get", mock_get):
                with pytest.raises(Exception, match="Quote API failed"):
                    await execute_solana_swap(mock_wallet, "EPjFW...", 0.05, 50)