import logging
from solders.keypair import Keypair
from cryptography.fernet import Fernet
from typing import Tuple

logger = logging.getLogger(__name__)

# Encryption key (move to config in production)
ENCRYPTION_KEY = Fernet.generate_key()
CIPHER = Fernet(ENCRYPTION_KEY)

def create_solana_wallet() -> Tuple[str, str]:
    """
    Generate a new Solana custodial wallet.

    Returns:
        Tuple[str, str]: (public_key, encrypted_private_key)

    Edge Cases:
    - Handle keypair generation failures.
    - Ensure private key is securely encrypted.
    """
    try:
        # Generate a new Solana keypair
        keypair = Keypair()
        public_key = str(keypair.public_key)  # Base58-encoded public key
        private_key = bytes(keypair.secret_key)  # Raw bytes of private key

        # Encrypt the private key for secure storage
        encrypted_private_key = CIPHER.encrypt(private_key).decode('utf-8')

        logger.info(f"Generated Solana wallet: {public_key}")
        return public_key, encrypted_private_key

    except Exception as e:
        logger.error(f"Failed to create Solana wallet: {str(e)}")
        raise ValueError(f"Solana wallet creation failed: {str(e)}")
