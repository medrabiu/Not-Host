import logging
from tonsdk.crypto import mnemonic_new
from tonsdk.contract.wallet import Wallets, WalletVersionEnum
from cryptography.fernet import Fernet
from typing import Tuple

logger = logging.getLogger(__name__)

# Encryption key (move to config in production)
ENCRYPTION_KEY = Fernet.generate_key()
CIPHER = Fernet(ENCRYPTION_KEY)

def create_ton_wallet() -> Tuple[str, str]:
    """
    Generate a new TON custodial wallet.

    Returns:
        Tuple[str, str]: (public_address, encrypted_private_key)
    """
    try:
        # Generate mnemonic and create v3r2 wallet
        mnemonics = mnemonic_new()
        _, _, private_key, wallet = Wallets.from_mnemonics(
            mnemonics=mnemonics,
            version=WalletVersionEnum.v3r2,
            workchain=0
        )

        # Get user-friendly address
        address = wallet.address.to_string(is_user_friendly=True)

        # Encrypt private key
        encrypted_private_key = CIPHER.encrypt(private_key).decode('utf-8')

        logger.info(f"Generated TON wallet: {address}")
        return address, encrypted_private_key

    except Exception as e:
        logger.error(f"Failed to create TON wallet: {str(e)}")
        raise ValueError(f"TON wallet creation failed: {str(e)}")
