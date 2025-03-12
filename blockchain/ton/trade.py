import logging
import aiohttp
from pytoniq_core import Address
from tonutils.client import TonapiClient
from tonutils.jetton.dex.stonfi import StonfiRouterV2
from tonutils.jetton.dex.stonfi.v2.pton.constants import PTONAddresses
from tonutils.utils import to_nano, to_amount
from tonutils.wallet import WalletV4R2
from services.crypto import CIPHER
from typing import Dict, Optional
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

API_KEY = os.getenv("API_KEY")
IS_TESTNET = os.getenv("IS_TESTNET", "False").lower() in ("true", "1", "yes")

SLIPPAGE_BPS = 50  # (e.g., 50 = 0.5%)
DECIMALS = 9


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
        offer_amount = to_nano(amount_ton, DECIMALS)  # Convert TON to nanoTON
        if offer_amount > wallet_balance_before:
            raise ValueError("Insufficient TON balance to cover the swap and gas fees.")

        # Get router address and swap parameters
        router_address = await get_router_address(token_mint, amount_ton, slippage_bps)
        if not router_address:
            raise ValueError("Failed to get a valid router address.")

        router = StonfiRouterV2(client, router_address=Address(router_address))

        # Calculate slippage
        min_amount_out = int(offer_amount * (1 - slippage_bps / 10000))  # Minimum output after slippage

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

        # Check transaction status
        tx_status = await check_transaction_status(client, tx_hash)
        if tx_status != "success":
            logger.error(f"Swap failed. TX Hash: {tx_hash}, Status: {tx_status}")
            raise ValueError(f"Swap failed. Status: {tx_status}")

        # Fetch wallet balance after swap
        wallet_balance_after = await client.get_account_balance(ton_wallet.address.to_str())
        logger.info(f"Wallet balance after swap: {wallet_balance_after} nanoTON")

        # Calculate gas fees
        gas_used = wallet_balance_before - wallet_balance_after - offer_amount
        logger.info(f"Gas fees used: {gas_used} nanoTON")

        return {"output_amount": min_amount_out, "tx_id": tx_hash}

    except Exception as e:
        logger.error(f"Failed to execute TON swap via STON.fi V2: {str(e)}", exc_info=True)
        raise


async def get_router_address(token_mint: str, amount_ton: float, slippage_bps: int) -> Optional[str]:
    """
    Fetch the correct router address using STON.fi API.

    Args:
        token_mint: Jetton Master address of the token to buy.
        amount_ton: Amount of TON to spend.
        slippage_bps: Slippage tolerance in basis points (e.g., 50 = 0.5%).

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

    logger.info(f"Fetching router address from STON.fi...")
    logger.info(f"Params: {params}")

    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params, headers=headers) as response:
            if response.status == 200:
                content = await response.json()
                router_address = content.get("router_address")
                pools = content.get("pools", [])

                logger.info(f"STON.fi Response: {content}")
                logger.info(f"Router Address: {router_address}")

                if not router_address:
                    raise ValueError("Router address not found in response.")

                if pools:
                    logger.info(f"Found {len(pools)} pool(s) in the route:")
                    for pool in pools:
                        logger.info(f"Pool: {pool}")

                # Expected and actual output comparison
                min_ask_units = content.get("min_ask_units")
                ask_units = content.get("ask_units")
                logger.info(f"Expected Output (min_ask_units): {min_ask_units}")
                logger.info(f"Actual Output (ask_units): {ask_units}")

                return router_address
            else:
                error_text = await response.text()
                logger.error(f"Failed to get router address. Status: {response.status}, Error: {error_text}")
                raise Exception(f"Failed to get router address: {response.status}: {error_text}")


async def check_transaction_status(client: TonapiClient, tx_hash: str) -> str:
    """
    Check the status of a transaction.

    Args:
        client: TonAPI client.
        tx_hash: Transaction hash.

    Returns:
        Transaction status (e.g., "success", "pending", "failed").
    """
    try:
        tx_details = await client.get_transaction(tx_hash)
        if tx_details["status"] == "success":
            logger.info(f"Transaction {tx_hash} confirmed successfully.")
            return "success"
        else:
            logger.warning(f"Transaction {tx_hash} status: {tx_details['status']}")
            return tx_details["status"]
    except Exception as e:
        logger.error(f"Failed to fetch transaction status: {str(e)}")
        return "unknown"

