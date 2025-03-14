# blockchain/ton/withdraw.py
import logging
import os
from tonsdk.provider import ToncenterClient  
from tonsdk.contract.wallet import Wallets, WalletVersionEnum
from tonsdk.utils import Address

logger = logging.getLogger(__name__)

async def send_ton_transaction(mnemonic: str, destination_address: str, nano_amount: int) -> str:
    """
    Send TON from the wallet identified by mnemonic to the destination address.
    Args:
        mnemonic: Wallet mnemonic phrase (space-separated words).
        destination_address: TON address to send to.
        nano_amount: Amount in nanoTON (1 TON = 10^9 nanoTON).
    Returns:
        Transaction ID as a string.
    Raises:
        ValueError: If the destination address is invalid or API key is missing.
        Exception: If the transaction fails.
    """
    try:
        # Load TonCenter API key from environment
        api_key = os.getenv("TON_API_KEY")
        if not api_key:
            raise ValueError("TON_API_KEY environment variable is not set")

        # Initialize TonCenter client
        client = ToncenterClient(api_key=api_key, network="mainnet")

        # Create wallet from mnemonic (using v4R2 as per your wallet.py default)
        mnemonics = mnemonic.split()
        _, _, private_key, wallet = Wallets.from_mnemonics(
            mnemonics=mnemonics,
            version=WalletVersionEnum.v4r2,
            workchain=0
        )

        # Validate destination address
        try:
            Address(destination_address)
        except Exception as e:
            raise ValueError(f"Invalid TON destination address: {str(e)}")

        # Prepare and send the transaction
        transfer = await wallet.transfer(
            destination=destination_address,
            amount=nano_amount,
            bounce=False,  # Non-bouncable to avoid issues with uninitialized addresses
            comment="Withdrawal via Not-Cotrader",
            client=client
        )

        # Extract transaction ID
        # Assuming transfer returns a dict with 'transaction_id'. Adjust if needed.
        tx_id = transfer.get("transaction_id")
        if not tx_id:
            raise ValueError("Transaction ID not found in response")
        
        logger.info(f"TON transaction sent: {tx_id}")
        return tx_id

    except Exception as e:
        logger.error(f"Failed to send TON transaction: {str(e)}", exc_info=True)
        raise Exception(f"TON transaction failed: {str(e)}")
