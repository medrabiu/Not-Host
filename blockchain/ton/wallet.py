import logging
from tonsdk.crypto import mnemonic_new
from tonsdk.contract.wallet import Wallets, WalletVersionEnum
from services.crypto import CIPHER  
from typing import Tuple
logger = logging.getLogger(__name__)

def create_ton_wallet(version: str = "v4R2") -> Tuple[str, str]:
    """
    Generate a new TON custodial wallet with a specified version (v4R2 or v5R1).

    This function creates a new TON wallet by generating a 24-word mnemonic phrase,
    deriving the wallet address and private key using the specified wallet version,
    and encrypting the mnemonic phrase for secure storage.

    Args:
        version (str, optional): Wallet version to use. Accepts 'v4R2' or 'v5R1'.
            Defaults to 'v4R2'. Falls back to 'v4R2' if 'v5R1' is unsupported.

    Returns:
        Tuple[str, str]: A tuple containing:
            - public_address (str): The TON wallet address in user-friendly, non-bounceable format.
            - encrypted_mnemonic (str): The encrypted 24-word mnemonic phrase as a UTF-8 encoded string.

    Raises:
        ValueError: If wallet creation fails due to mnemonic generation, key derivation,
            or encryption errors.

    Notes:
        - Uses the tonsdk library to generate mnemonics and derive wallet details.
        - The mnemonic phrase is encrypted instead of the private key for recovery purposes.
        - If 'v5R1' is specified but not supported by the tonsdk version, it falls back to 'v4R2'
          with a logged warning.
    """
    try:
        wallet_version = (
            WalletVersionEnum.v4r2 if version == "v4R2"
            else WalletVersionEnum.v5r1 if version == "v5R1" and hasattr(WalletVersionEnum, "v5r1")
            else WalletVersionEnum.v4r2
        )
        if version == "v5R1" and not hasattr(WalletVersionEnum, "v5r1"):
            logger.warning("v5R1 not supported in this tonsdk version; falling back to v4R2")
            wallet_version = WalletVersionEnum.v4r2

        mnemonics = mnemonic_new()  # 24-word mnemonic phrase
        mnemonic_str = " ".join(mnemonics)  # Convert list to string
        _, _, private_key, wallet = Wallets.from_mnemonics(
            mnemonics=mnemonics,
            version=wallet_version,
            workchain=0
        )

        address = wallet.address.to_string(
            is_user_friendly=True,
            is_bounceable=False
        ).strip()

        # Encrypt the mnemonic phrase instead of the private key
        encrypted_mnemonic = CIPHER.encrypt(mnemonic_str.encode('utf-8')).decode('utf-8')

        logger.info(f"Generated TON wallet: {address} (version: {wallet_version})")
        return address, encrypted_mnemonic

    except Exception as e:
        logger.error(f"Failed to create TON wallet: {str(e)}")
        raise ValueError(f"TON wallet creation failed: {str(e)}")