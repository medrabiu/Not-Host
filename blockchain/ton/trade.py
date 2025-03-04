import logging
import os
from pytoniq_core import Address
from tonutils.client import TonapiClient
from tonutils.jetton.dex.stonfi import StonfiRouterV1
from tonutils.utils import to_nano
from tonutils.wallet import WalletV4R2
from services.crypto import CIPHER
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Use environment variable with fallback for API key
API_KEY = os.getenv("TON_API_KEY", "AGVENPU5U7V6FDQAAAAEOR3JTJPI7Q7EFPHIOEUOEVVEHZ452BPDMPC2JCBNKBBWTJMHCBI")
IS_TESTNET = os.getenv("TON_TESTNET", "False").lower() in ("true", "1", "t")  # Default to mainnet unless explicitly set

async def execute_ton_swap(wallet, token_mint: str, amount_ton: float, slippage_bps: int) -> Dict:
    """
    Execute a token swap on TON using STON.fi DEX with robust error handling.

    Args:
        wallet: Wallet object with encrypted_private_key (mnemonic) and public_key.
        token_mint: The Jetton Master address of the token to buy.
        amount_ton: Amount of TON to spend (must be positive).
        slippage_bps: Slippage tolerance in basis points (0-10000, e.g., 50 = 0.5%).

    Returns:
        Dict with output_amount (in nano units) and tx_id.

    Raises:
        ValueError: For invalid inputs or wallet state.
        Exception: For API or transaction failures.
    """
    try:
        # Validate inputs
        if not API_KEY:
            raise ValueError("TON_API_KEY environment variable is not set")
        if not wallet or not hasattr(wallet, 'encrypted_private_key') or not hasattr(wallet, 'public_key'):
            raise ValueError("Invalid wallet object provided")
        if not token_mint or not isinstance(token_mint, str):
            raise ValueError("Token mint address must be a non-empty string")
        if amount_ton <= 0:
            raise ValueError(f"Amount TON must be positive, got {amount_ton}")
        if not 0 <= slippage_bps <= 10000:
            raise ValueError(f"Slippage must be between 0 and 10000 bps, got {slippage_bps}")

        logger.info(f"Executing TON swap: {amount_ton} TON -> {token_mint} with {slippage_bps} bps slippage "
                    f"(testnet: {IS_TESTNET})")

        # Initialize client
        client = TonapiClient(api_key=API_KEY, is_testnet=IS_TESTNET)
        logger.debug(f"Initialized TonapiClient with API key ending in {API_KEY[-4:]}")

        # Decrypt and validate mnemonic
        try:
            decrypted_mnemonic = CIPHER.decrypt(wallet.encrypted_private_key.encode('utf-8')).decode('utf-8')
            mnemonic_list = decrypted_mnemonic.split()
            if len(mnemonic_list) != 24:
                raise ValueError(f"Invalid mnemonic length: expected 24 words, got {len(mnemonic_list)}")
        except Exception as e:
            raise ValueError(f"Failed to decrypt or parse mnemonic: {str(e)}")

        # Create wallet instance
        ton_wallet, _, _, _ = WalletV4R2.from_mnemonic(client, mnemonic_list)
        if ton_wallet.address.to_str() != wallet.public_key:
            raise ValueError(f"Wallet address mismatch: decrypted {ton_wallet.address.to_str()} != stored {wallet.public_key}")

        # Check balance (optional, requires additional API call; stubbed for now)
        # balance_nano = await get_ton_balance(wallet.public_key, client)  # Uncomment if balance check added
        # if balance_nano < offer_amount + to_nano(0.01, 9):
        #     raise ValueError(f"Insufficient TON balance: {balance_nano / 1e9} < {(offer_amount + to_nano(0.01, 9)) / 1e9}")

        # Use STON.fi Router V1 for swap
        router = StonfiRouterV1(client)
        offer_amount = to_nano(amount_ton, 9)  # TON uses 9 decimals
        min_amount_out = int(offer_amount * (1 - slippage_bps / 10000))  # Apply slippage
        logger.debug(f"Swap params: offer={amount_ton} TON, min_out={min_amount_out / 1e9} Jetton units")

        try:
            to, value, body = await router.get_swap_ton_to_jetton_tx_params(
                user_wallet_address=ton_wallet.address,
                ask_jetton_address=Address(token_mint),
                offer_amount=offer_amount,
                min_ask_amount=min_amount_out
            )
        except Exception as e:
            raise Exception(f"Failed to get STON.fi swap parameters: {str(e)}")

        # Execute the swap
        try:
            tx_hash = await ton_wallet.transfer(
                destination=to,
                amount=value,
                body=body
            )
        except Exception as e:
            raise Exception(f"Failed to send swap transaction: {str(e)}")

        # Placeholder output amount (actual requires post-confirmation fetch)
        output_amount = min_amount_out
        logger.info(f"TON swap transaction sent via STON.fi: {tx_hash}")

        return {"output_amount": output_amount, "tx_id": tx_hash}

    except ValueError as ve:
        logger.error(f"Validation error in TON swap: {str(ve)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in TON swap: {str(e)}", exc_info=True)
        raise