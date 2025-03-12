import logging
import aiohttp
import os
from pytoniq_core import Address
from tonutils.client import TonapiClient
from tonutils.jetton.dex.stonfi import StonfiRouterV2
from tonutils.jetton.dex.stonfi.v2.pton.constants import PTONAddresses
from tonutils.utils import to_nano, to_amount
from tonutils.wallet import WalletV4R2
from services.crypto import CIPHER
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Configs
API_KEY = "AGVENPU5U7V6FDQAAAAEOR3JTJPI7Q7EFPHIOEUOEVVEHZ452BPDMPC2JCBNKBBWTJMHCBI"
IS_TESTNET = os.getenv("IS_TESTNET", False)
SLIPPAGE_BPS = 50  # (e.g., 50 = 0.5%)
DECIMALS = 9
MAX_RETRIES = 3


async def execute_ton_swap(wallet, token_mint: str, amount_ton: float, slippage_bps: int = SLIPPAGE_BPS) -> Dict:
    """
    Execute a token swap on TON using STON.fi DEX (V2).

    Args:
        wallet: Wallet object with encrypted_private_key and public_key.
        token_mint: The Jetton Master address of the token to buy.
        amount_ton: Amount of TON to spend.
        slippage_bps: Slippage tolerance in basis points (e.g., 50 = 0.5%).

    Returns:
        Dict with output_amount (in nano units) and tx_id.
    """
    try:
        # Initialize TonAPI client
        client = TonapiClient(api_key=API_KEY, is_testnet=IS_TESTNET)

        # Decrypt mnemonic from wallet
        decrypted_mnemonic = CIPHER.decrypt(wallet.encrypted_private_key.encode('utf-8')).decode('utf-8')
        mnemonic_list = decrypted_mnemonic.split()
        ton_wallet, _, _, _ = WalletV4R2.from_mnemonic(client, mnemonic_list)

        # Fetch wallet balance before swap
        wallet_balance_before = await client.get_account_balance(ton_wallet.address.to_str())
        logger.info(f"Wallet balance before swap: {wallet_balance_before} nanoTON")

        # Ensure enough balance (including gas fees)
        offer_amount = to_nano(amount_ton, DECIMALS)
        if offer_amount > wallet_balance_before:
            raise ValueError("Insufficient TON balance to cover the swap and gas fees.")

        # Get the router address (with retry logic)
        router_address = await get_router_address(token_mint, amount_ton, slippage_bps)
        if not router_address:
            raise ValueError("Router address not found. Cannot proceed with swap.")

        # Initialize router with fetched address
        router = StonfiRouterV2(client, router_address=Address(router_address))

        # Calculate minimum output with slippage
        min_amount_out = int(offer_amount * (1 - slippage_bps / 10000))

        # Fetch swap transaction parameters
        to, value, body = await router.get_swap_ton_to_jetton_tx_params(
            user_wallet_address=ton_wallet.address,
            receiver_address=ton_wallet.address,
            offer_jetton_address=Address(token_mint),
            offer_amount=offer_amount,
            min_ask_amount=min_amount_out,
            refund_address=ton_wallet.address,
        )

        # Execute the swap transaction
        tx_hash = await ton_wallet.transfer(
            destination=to,
            amount=to_amount(value),
            body=body,
        )
        logger.info(f"TON swap transaction sent via STON.fi (V2): {tx_hash}")

        # Verify the transaction status
        tx_status = await check_transaction_status(client, ton_wallet.address, tx_hash)
        if not tx_status:
            raise Exception(f"Transaction {tx_hash} failed or not found!")

        # Fetch wallet balance after swap
        wallet_balance_after = await client.get_account_balance(ton_wallet.address.to_str())
        logger.info(f"Wallet balance after swap: {wallet_balance_after} nanoTON")

        # Calculate gas fees
        gas_used = wallet_balance_before - wallet_balance_after - offer_amount
        logger.info(f"Gas fees used: {gas_used} nanoTON")

        return {"output_amount": min_amount_out, "tx_id": tx_hash}

    except Exception as e:
        logger.error(f"Failed to execute TON swap via STON.fi V2: {str(e)}", exc_info=True)
        return {"error": str(e)}


async def get_router_address(token_mint: str, amount_ton: float, slippage_bps: int, retries=MAX_RETRIES) -> Optional[str]:
    """
    Fetch the correct router address using STON.fi API with retry logic.

    Args:
        token_mint: Jetton Master address of the token to buy.
        amount_ton: Amount of TON to spend.
        slippage_bps: Slippage tolerance in basis points (e.g., 50 = 0.5%).
        retries: Number of retries in case of failure.

    Returns:
        The router address as a string.
    """
    url = "https://api.ston.fi/v1/swap/simulate"
    headers = {"Accept": "application/json"}

    params = {
        "offer_address": PTONAddresses.TESTNET if IS_TESTNET else PTONAddresses.MAINNET,
        "ask_address": token_mint,
        "units": to_nano(amount_ton, DECIMALS),
        "slippage_tolerance": slippage_bps / 100,
        "dex_v2": "true",
    }

    for attempt in range(retries):
        try:
            logger.info(f"Fetching router address (Attempt {attempt + 1}/{retries})...")
            async with aiohttp.ClientSession() as session:
                async with session.post(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        content = await response.json()
                        router_address = content.get("router_address")
                        logger.info(f"Router Address: {router_address}")

                        if not router_address:
                            raise ValueError("Router address not found in response.")
                        return router_address
                    else:
                        error_text = await response.text()
                        logger.warning(f"Failed to get router address (Attempt {attempt + 1}): {error_text}")

        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")

    logger.error("Failed to fetch router address after retries.")
    return None


async def check_transaction_status(client, wallet_address: str, tx_hash: str) -> bool:
    """
    Check transaction status using TonAPI.

    Args:
        client: TonAPI Client.
        wallet_address: Address of the wallet that executed the transaction.
        tx_hash: Transaction hash to check.

    Returns:
        True if transaction is successful, False otherwise.
    """
    try:
        logger.info(f"Checking transaction status for {tx_hash}...")
        tx_info = await client.get_transactions(wallet_address, limit=5)
        for tx in tx_info:
            if tx.get("hash") == tx_hash:
                logger.info("Transaction confirmed.")
                return True
        logger.warning("Transaction not found in recent transactions.")
        return False
    except Exception as e:
        logger.error(f"Failed to check transaction status: {str(e)}")
        return False
