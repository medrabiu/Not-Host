import logging
import os
from pytoniq_core import Address
from tonutils.client import TonapiClient
from tonutils.jetton.dex.stonfi import StonfiRouterV1
from tonutils.utils import to_nano, to_amount
from tonutils.wallet import WalletV4R2
from services.crypto import CIPHER
from typing import Dict

logger = logging.getLogger(__name__)

API_KEY = "AGVENPU5U7V6FDQAAAAEOR3JTJPI7Q7EFPHIOEUOEVVEHZ452BPDMPC2JCBNKBBWTJMHCBI"
IS_TESTNET = False  # Set to True for testnet during development

async def execute_ton_swap(wallet, token_mint: str, amount_ton: float, slippage_bps: int) -> Dict:
    """
    Execute a token swap on TON using STON.fi DEX.

    Args:
        wallet: Wallet object with encrypted_private_key and public_key.
        token_mint: The Jetton Master address of the token to buy.
        amount_ton: Amount of TON to spend.
        slippage_bps: Slippage tolerance in basis points (e.g., 50 = 0.5%).

    Returns:
        Dict with output_amount (in nano units) and tx_id.
    """
    try:
        client = TonapiClient(api_key=API_KEY, is_testnet=IS_TESTNET)
        # Decrypt mnemonic from wallet
        decrypted_mnemonic = CIPHER.decrypt(wallet.encrypted_private_key.encode('utf-8')).decode('utf-8')
        mnemonic_list = decrypted_mnemonic.split()
        ton_wallet, _, _, _ = WalletV4R2.from_mnemonic(client, mnemonic_list)

        # Use STON.fi Router V1 for swap
        router = StonfiRouterV1(client)
        offer_amount = to_nano(amount_ton, 9)  # TON uses 9 decimals
        min_amount_out = int(offer_amount * (1 - slippage_bps / 10000))  # Apply slippage
        to, value, body = await router.get_swap_ton_to_jetton_tx_params(
            user_wallet_address=ton_wallet.address,
            ask_jetton_address=Address(token_mint),  # Correct parameter from reference
            offer_amount=offer_amount,
            min_ask_amount=min_amount_out  # Minimum output after slippage
        )

        # Execute the swap
        tx_hash = await ton_wallet.transfer(
            destination=to,
            amount=value,  # Use raw nanoTON value
            body=body
        )

        # Placeholder output amount (actual requires confirmation or quote API)
        output_amount = min_amount_out  # Update with real amount post-confirmation
        logger.info(f"TON swap transaction sent via STON.fi: {tx_hash}")

        return {"output_amount": output_amount, "tx_id": tx_hash}

    except Exception as e:
        logger.error(f"Failed to execute TON swap via STON.fi: {str(e)}", exc_info=True)
        raise
