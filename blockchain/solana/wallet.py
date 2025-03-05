import logging
from services.crypto import CIPHER  # Import CIPHER from services/crypto
from typing import Tuple
from solders.keypair import Keypair

logger = logging.getLogger(__name__)

def create_solana_wallet() -> Tuple[str, str]:
    """
    Generate a new Solana custodial wallet with an encrypted private key.

    This function creates a new Solana keypair, extracts the public key as a string,
    and encrypts the private key using the CIPHER object from services.crypto.

    Returns:
        Tuple[str, str]: A tuple containing:
            - public_key (str): The Solana wallet's public key.
            - encrypted_private_key (str): The encrypted private key as a UTF-8 encoded string.

    Raises:
        ValueError: If keypair generation or encryption fails due to an underlying exception.

    Notes:
        - The private key is encrypted to ensure security.
        - Any failure in keypair generation or encryption is logged and raised as an exception.
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