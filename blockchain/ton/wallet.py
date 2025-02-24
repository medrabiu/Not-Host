import logging
from tonsdk.crypto import mnemonic_new
from tonsdk.contract.wallet import Wallets, WalletVersionEnum
from cryptography.fernet import Fernet
from typing import Tuple

logger = logging.getLogger(__name__)

# Encryption key (move to config in production)
ENCRYPTION_KEY = Fernet.generate_key()
CIPHER = Fernet(ENCRYPTION_KEY)

def create_ton_wallet(version: str = "v4R2") -> Tuple[str, str]:
    """
    Generate a new TON custodial wallet with a specified version (v4R2 or v5R1).

    Args:
        version: Wallet version to use ('v4R2' or 'v5R1', default 'v4R2').

    Returns:
        Tuple[str, str]: (public_address, encrypted_private_key)
    """
    try:
        # Select wallet version
        wallet_version = (
            WalletVersionEnum.v4r2 if version == "v4R2"
            else WalletVersionEnum.v5r1 if version == "v5R1" and hasattr(WalletVersionEnum, "v5r1")
            else WalletVersionEnum.v4r2  # Default to v4R2 if v5R1 unsupported
        )
        if version == "v5R1" and not hasattr(WalletVersionEnum, "v5r1"):
            logger.warning("v5R1 not supported in this tonsdk version; falling back to v4R2")
            wallet_version = WalletVersionEnum.v4r2

        # Generate mnemonic and create wallet
        mnemonics = mnemonic_new()
        _, _, private_key, wallet = Wallets.from_mnemonics(
            mnemonics=mnemonics,
            version=wallet_version,
            workchain=0
        )

        # Get user-friendly, non-bounceable (UQ) address
        address = wallet.address.to_string(
            is_user_friendly=True,
            is_bounceable=False  # Ensures UQ address
        )

        # Encrypt private key
        encrypted_private_key = CIPHER.encrypt(private_key).decode('utf-8')

        logger.info(f"Generated TON wallet: {address} (version: {wallet_version})")
        return address, encrypted_private_key

    except Exception as e:
        logger.error(f"Failed to create TON wallet: {str(e)}")
        raise ValueError(f"TON wallet creation failed: {str(e)}")