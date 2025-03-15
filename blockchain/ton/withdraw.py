# blockchain/ton/withdraw.py
import logging
import os
from tonutils.client import TonapiClient
from tonutils.wallet import WalletV4R2

logger = logging.getLogger(__name__)

async def send_ton_transaction(mnemonic: str, destination_address: str, nano_amount: int) -> str:
    """
    Send TON from the wallet identified by mnemonic to the destination address using tonutils.
    Args:
        mnemonic: Wallet mnemonic phrase (space-separated words).
        destination_address: TON address to send to.
        nano_amount: Amount in nanoTON (1 TON = 10^9 nanoTON).
    Returns:
        Transaction hash as a string.
    Raises:
        ValueError: If the API key is missing or destination address is invalid.
        Exception: If the transaction fails.
    """
    try:
        # Load Tonapi API key from environment
        api_key = os.getenv("TON_API_KEY")
        if not api_key:
            raise ValueError("TON_API_KEY environment variable is not set")

        # Initialize Tonapi client (set IS_TESTNET=True for testnet, False for mainnet)
        is_testnet = os.getenv("TON_IS_TESTNET", "False").lower() == "true"  # Optional: configurable via env
        client = TonapiClient(api_key=api_key, is_testnet=is_testnet)

        # Create wallet from mnemonic
        mnemonic_list = mnemonic.split()
        wallet, _, _, _ = WalletV4R2.from_mnemonic(client, mnemonic_list)

        # Convert nanoTON to TON (tonutils expects TON, not nanoTON)
        amount_ton = nano_amount / 1_000_000_000

        # Validate destination address (basic check; tonutils may do more internally)
        if not destination_address.startswith("EQ") and not destination_address.startswith("UQ"):
            raise ValueError("Invalid TON destination address: Must start with 'EQ' or 'UQ'")

        # Send the transaction
        tx_hash = await wallet.transfer(
            destination=destination_address,
            amount=amount_ton,
            body="Withdrawal via Not-Cotrader"
        )

        logger.info(f"TON transaction sent: {tx_hash}")
        return tx_hash

    except Exception as e:
        logger.error(f"Failed to send TON transaction: {str(e)}", exc_info=True)
        raise Exception(f"TON transaction failed: {str(e)}")