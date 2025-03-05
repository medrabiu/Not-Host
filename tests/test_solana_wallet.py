import pytest
from unittest.mock import patch
from solders.keypair import Keypair
from blockchain.solana.wallet import create_solana_wallet
from services.crypto import CIPHER

@pytest.mark.asyncio
async def test_create_solana_wallet_success():
    """Test successful Solana wallet creation."""
    mock_keypair = Keypair()
    mock_encrypted = "encrypted_key".encode('utf-8')  # Match expected output type
    with patch("solders.keypair.Keypair", return_value=mock_keypair):
        with patch.object(CIPHER, "encrypt", return_value=mock_encrypted):
            address, encrypted_key = await create_solana_wallet()
            assert address == str(mock_keypair.pubkey())
            assert encrypted_key == "encrypted_key"