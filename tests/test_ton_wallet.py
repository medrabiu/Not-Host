import pytest
from unittest.mock import patch, Mock
from blockchain.ton.wallet import create_ton_wallet
from services.crypto import CIPHER

def test_create_ton_wallet_success_v4r2():
    """Test successful TON wallet creation with v4R2 version."""
    mock_mnemonics = ["word"] * 24
    mock_wallet = Mock()
    mock_wallet.address.to_string.return_value = "EQAYpxYkdsiJoOxnBqhrx5XkEyUNbRk0oHDnMIaKHiWTcRRv"

    with patch("tonsdk.crypto.mnemonic_new", return_value=mock_mnemonics):
        with patch("tonsdk.contract.wallet.Wallets.from_mnemonics", return_value=(None, None, None, mock_wallet)):
            with patch.object(CIPHER, "encrypt", return_value="encrypted_mnemonic"):
                address, encrypted_key = create_ton_wallet(version="v4R2")
                assert address == "EQAYpxYkdsiJoOxnBqhrx5XkEyUNbRk0oHDnMIaKHiWTcRRv"
                assert encrypted_key == "encrypted_mnemonic"

def test_create_ton_wallet_invalid_version():
    """Test wallet creation with invalid version falls back to v4R2."""
    mock_mnemonics = ["word"] * 24
    mock_wallet = Mock()
    mock_wallet.address.to_string.return_value = "EQAYpxYkdsiJoOxnBqhrx5XkEyUNbRk0oHDnMIaKHiWTcRRv"

    with patch("tonsdk.crypto.mnemonic_new", return_value=mock_mnemonics):
        with patch("tonsdk.contract.wallet.Wallets.from_mnemonics", return_value=(None, None, None, mock_wallet)):
            with patch.object(CIPHER, "encrypt", return_value="encrypted_mnemonic"):
                address, encrypted_key = create_ton_wallet(version="invalid")
                assert address == "EQAYpxYkdsiJoOxnBqhrx5XkEyUNbRk0oHDnMIaKHiWTcRRv"
                assert encrypted_key == "encrypted_mnemonic"
@pytest.mark.asyncio
async def test_create_ton_wallet_encryption_failure():
    """Test wallet creation with encryption failure."""
    mock_mnemonics = ["word"] * 24
    mock_wallet = Mock()
    mock_wallet.address.to_string.return_value = "EQAYpxYkdsiJoOxnBqhrx5XkEyUNbRk0oHDnMIaKHiWTcRRv"

    with patch("tonsdk.crypto.mnemonic_new", return_value=mock_mnemonics):
        with patch("tonsdk.contract.wallet.Wallets.from_mnemonics", return_value=(None, None, None, mock_wallet)):
            with patch.object(CIPHER, "encrypt", side_effect=Exception("Encryption failed")):
                with pytest.raises(ValueError, match="TON wallet creation failed: Encryption failed"):
                    await create_ton_wallet(version="v4R2")