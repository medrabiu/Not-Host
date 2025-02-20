import logging
from tonsdk.crypto import mnemonic_new, Keypair as TonKeypair
from tonsdk.utils import Address
from cryptography.fernet import Fernet
from typing import Tuple

logger = logging.getLogger(__name__)

# Reuse the same encryption key as Solana (move to config in production)
ENCRYPTION_KEY = Fernet.generate_key()
CIPHER = Fernet(ENCRYPTION_KEY)

def create_ton_wallet() -> Tuple[str, str]:
    """
    Generate a new TON custodial wallet using mnemonic.

    Returns:
        Tuple[str, str]: (public_address, encrypted_private_key)

    Edge Cases:
    - Handle mnemonic or keypair generation failures.
    - Ensure private key encryption succeeds.
    """
    try:
        # Generate a new mnemonic and derive keypair (TON v3 wallet standard)
        mnemonic = mnemonic_new()
        keypair = TonKeypair.from_mnemonic(mnemonic)
        public_key = keypair.public_key
        private_key = keypair.secret_key  # Raw bytes

        # TON address derivation (simplified; use TON client for exact format in production)
        address = Address.from_public_key(public_key).to_string(is_user_friendly=True)

        # Encrypt the private key
        encrypted_private_key = CIPHER.encrypt(private_key).decode('utf-8')

        logger.info(f"Generated TON wallet: {address}")
        return address, encrypted_private_key

    except Exception as e:
        logger.error(f"Failed to create TON wallet: {str(e)}")
        raise ValueError(f"TON wallet creation failed: {str(e)}")
