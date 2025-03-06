import pytest
from unittest.mock import patch, MagicMock
from blockchain.solana.wallet import create_solana_wallet  # Adjust based on actual module
from services.crypto import CIPHER  # Adjust import based on actual module

def test_create_solana_wallet_success():
    mock_private_key = b"MockPrivateKey123"
    mock_encrypted_private_key = "EncryptedMockPrivateKey"

    with patch("solders.keypair.Keypair") as mock_keypair, \
         patch.object(CIPHER, "encrypt", return_value=mock_encrypted_private_key.encode('utf-8')):

        mock_keypair_instance = MagicMock()
        mock_keypair_instance.pubkey.return_value.to_base58.return_value = "GeneratedPublicKey123"  # Mock valid key format
        mock_keypair_instance.secret.return_value = mock_private_key
        mock_keypair.return_value = mock_keypair_instance

        public_key, encrypted_private_key = create_solana_wallet()

        assert isinstance(public_key, str)  # Ensure it's a string
        assert len(public_key) > 30  # Rough length check for Solana public key
        assert encrypted_private_key == mock_encrypted_private_key

def test_create_solana_wallet_encryption_failure():
    with patch("solders.keypair.Keypair") as mock_keypair, \
         patch.object(CIPHER, "encrypt", side_effect=Exception("Encryption error")):
        
        mock_keypair_instance = MagicMock()
        mock_keypair_instance.pubkey.return_value.to_base58.return_value = "GeneratedPublicKey123"
        mock_keypair_instance.secret.return_value = b"MockPrivateKey123"
        mock_keypair.return_value = mock_keypair_instance

        with pytest.raises(ValueError, match="Solana wallet creation failed: Encryption error"):
            create_solana_wallet()

def test_create_solana_wallet_keypair_failure():
    with patch("solders.keypair.Keypair.__init__", side_effect=Exception("Keypair error")):
        with pytest.raises(ValueError, match="Solana wallet creation failed: Keypair error"):
            create_solana_wallet()