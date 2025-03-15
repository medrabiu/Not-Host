# blockchain/ton/withdraw.py
import logging
import os
from tonutils.client import TonapiClient
from tonutils.wallet import WalletV4R2
from pytoniq_core import Address

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
        logger.debug(f"Using TON_API_KEY: {api_key[:4]}... (masked)")

        # Initialize Tonapi client
        is_testnet = os.getenv("TON_IS_TESTNET", "False").lower() == "true"
        logger.debug(f"Network: {'testnet' if is_testnet else 'mainnet'}")
        client = TonapiClient(api_key=api_key, is_testnet=is_testnet)

        # Create wallet from mnemonic
        mnemonic_list = mnemonic.split()
        logger.debug(f"Mnemonic word count: {len(mnemonic_list)}")
        if len(mnemonic_list) != 24:  # Standard TON mnemonic is 24 words
            raise ValueError(f"Invalid mnemonic: Expected 24 words, got {len(mnemonic_list)}")
        wallet, _, _, _ = WalletV4R2.from_mnemonic(client, mnemonic_list)
        wallet_address = wallet.address.to_str(is_bounceable=False)
        logger.debug(f"Wallet address: {wallet_address}")

        # Validate amount and destination
        if not isinstance(nano_amount, int) or nano_amount <= 0:
            raise ValueError("Amount must be a positive integer in nanoTON")
        amount_ton = nano_amount / 1_000_000_000
        logger.debug(f"Amount: {amount_ton} TON ({nano_amount} nanoTON)")
        
        try:
            Address(destination_address)
            logger.debug(f"Destination address validated: {destination_address}")
        except Exception:
            raise ValueError(f"Invalid TON destination address: {destination_address}")

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