import pytest
from unittest.mock import patch, MagicMock
from services.crypto import CIPHER
from tonsdk.crypto import mnemonic_new
from tonsdk.contract.wallet import Wallets
from blockchain.ton.wallet import create_ton_wallet  # Adjust import to match your module

@pytest.fixture
def mock_mnemonic():
    return ["word" + str(i) for i in range(1, 25)]  # Fake 24-word mnemonic

def test_create_ton_wallet_success(mock_mnemonic):
    mock_address = "EQD3z-abc123xyz456"  # Fake TON address
    mock_encrypted_mnemonic = "EncryptedMnemonicData"

    with patch("tonsdk.crypto.mnemonic_new", return_value=mock_mnemonic), \
         patch("tonsdk.contract.wallet.Wallets.from_mnemonics") as mock_wallets, \
         patch.object(CIPHER, "encrypt", return_value=mock_encrypted_mnemonic.encode('utf-8')):

        mock_wallet_instance = MagicMock()
        mock_wallet_instance.address.to_string.return_value = mock_address
        mock_wallets.return_value = (None, None, None, mock_wallet_instance)

        address, encrypted_mnemonic = create_ton_wallet()

        assert address == mock_address
        assert encrypted_mnemonic == mock_encrypted_mnemonic

def test_create_ton_wallet_encryption_failure(mock_mnemonic):
    with patch("tonsdk.crypto.mnemonic_new", return_value=mock_mnemonic), \
         patch("tonsdk.contract.wallet.Wallets.from_mnemonics") as mock_wallets, \
         patch.object(CIPHER, "encrypt", side_effect=Exception("Encryption error")):

        mock_wallet_instance = MagicMock()
        mock_wallet_instance.address.to_string.return_value = "EQD3z-abc123xyz456"
        mock_wallets.return_value = (None, None, None, mock_wallet_instance)

        with pytest.raises(ValueError, match="TON wallet creation failed: Encryption error"):
            create_ton_wallet()

def test_create_ton_wallet_mnemonic_failure():
    with patch("tonsdk.crypto.mnemonic_new", side_effect=Exception("Mnemonic error")):
        try:
            create_ton_wallet()
        except Exception as e:
            print(f"Caught exception: {e}")  # Debugging output
            raise  
def test_create_ton_wallet_mnemonic_failure():
    with patch("tonsdk.crypto.mnemonic_new", side_effect=Exception("Mnemonic error")):
        try:
            create_ton_wallet()
        except Exception as e:
            print(f"Caught exception: {e}")  # Debugging output
            raise  