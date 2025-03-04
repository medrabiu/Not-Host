import logging
import os
from typing import Dict

from pytoniq_core import Address
from tonutils.client import TonapiClient
from tonutils.jetton.dex.stonfi import StonfiRouterV1
from tonutils.utils import to_nano
from tonutils.wallet import WalletV4R2
from services.crypto import CIPHER

logger = logging.getLogger(__name__)

# Configuration constants
API_KEY = os.getenv("TON_API_KEY")
IS_TESTNET = False  # Mainnet operation
JETTON_DECIMALS = 9  # Standard TON Jetton decimals
GAS_BUFFER = to_nano(0.05, JETTON_DECIMALS)  # Additional gas buffer
MAX_RETRIES = 3  # Retry attempts for transient failures


async def execute_ton_swap(
    wallet, token_mint: str, amount_ton: float, slippage_bps: int
) -> Dict:
    """
    Execute a token swap on TON mainnet using STON.fi DEX.

    Args:
        wallet: Wallet object with encrypted_private_key (mnemonic) and public_key.
        token_mint: Jetton Master address of the token to buy.
        amount_ton: Amount of TON to spend for the swap (excluding gas).
        slippage_bps: Slippage tolerance in basis points (e.g., 50 for 0.5%).

    Returns:
        Dict with 'output_amount' (in nano units) and 'tx_id'.

    Raises:
        ValueError: If inputs or API key are invalid.
        RuntimeError: If swap fails after retries or due to network issues.
    """
    if not API_KEY:
        logger.error("TON_API_KEY environment variable is not set")
        raise ValueError("TON_API_KEY environment variable is not set")

    if not isinstance(amount_ton, (int, float)) or amount_ton <= 0:
        logger.error(f"Invalid swap amount: {amount_ton}")
        raise ValueError("Swap amount must be a positive number")
    if not isinstance(slippage_bps, (int, float)) or slippage_bps < 0:
        logger.error(f"Invalid slippage: {slippage_bps}")
        raise ValueError("Slippage must be non-negative")
    if not token_mint or not isinstance(token_mint, str):
        logger.error("Invalid token mint address: None or not a string")
        raise ValueError("Token mint address must be a non-empty string")

    client = TonapiClient(api_key=API_KEY, is_testnet=IS_TESTNET)
    try:
        # Decrypt mnemonic and create wallet
        mnemonic = CIPHER.decrypt(wallet.encrypted_private_key.encode("utf-8")).decode("utf-8")
        mnemonic_list = mnemonic.split()
        if len(mnemonic_list) != 24:
            logger.error(f"Invalid mnemonic length: {len(mnemonic_list)} words")
            raise ValueError("Mnemonic must contain 24 words")

        ton_wallet, _, _, _ = WalletV4R2.from_mnemonic(client, mnemonic_list)
        logger.debug(f"Using wallet address: {ton_wallet.address.to_str()}")

        # Prepare swap parameters
        router = StonfiRouterV1(client)
        offer_amount = to_nano(amount_ton, JETTON_DECIMALS)
        min_amount_out = int(offer_amount * (1 - slippage_bps / 10000))
        total_amount = offer_amount + GAS_BUFFER

        # Execute swap with retries
        for attempt in range(MAX_RETRIES):
            try:
                to, value, body = await router.get_swap_ton_to_jetton_tx_params(
                    user_wallet_address=ton_wallet.address,
                    ask_jetton_address=Address(token_mint),
                    offer_amount=offer_amount,
                    min_ask_amount=min_amount_out,
                )

                tx_hash = await ton_wallet.transfer(
                    destination=to,
                    amount=total_amount,  # Include gas buffer
                    body=body,
                )
                break
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Swap attempt {attempt + 1} failed: {e}. Retrying...")
                    continue
                logger.error(f"Swap failed after {MAX_RETRIES} attempts: {e}")
                raise RuntimeError(f"Swap failed after {MAX_RETRIES} attempts: {e}")

        output_amount = min_amount_out  # Placeholder; update with actual amount later
        logger.info(
            f"TON swap executed via STON.fi: tx_hash={tx_hash}, "
            f"total_amount={total_amount / 1_000_000_000} TON"
        )
        return {"output_amount": output_amount, "tx_id": tx_hash}

    except Exception as e:
        logger.error(f"Failed to execute TON swap: {e}", exc_info=True)
        raise RuntimeError(f"TON swap execution failed: {e}")
 