import logging
from services.crypto import CIPHER  # Import CIPHER from services/crypto
from typing import Tuple
from solders.keypair import Keypair

logger = logging.getLogger(__name__)

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
        keypair = Keypair()
        public_key = str(keypair.pubkey())
        private_key = bytes(keypair.secret())

        encrypted_private_key = CIPHER.encrypt(private_key).decode('utf-8')

        logger.info(f"Generated Solana wallet: {public_key}")
        return public_key, encrypted_private_key

    except Exception as e:
        logger.error(f"Failed to create Solana wallet: {str(e)}")
        raise ValueError(f"Solana wallet creation failed: {str(e)}")