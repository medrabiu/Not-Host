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
from typing import Dict

logger = logging.getLogger(__name__)

# Configs
API_KEY = "AGVENPU5U7V6FDQAAAAEOR3JTJPI7Q7EFPHIOEUOEVVEHZ452BPDMPC2JCBNKBBWTJMHCBI"
IS_TESTNET = os.getenv("IS_TESTNET", False)
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
        client = TonapiClient(api_key=API_KEY, is_testnet=IS_TESTNET)

        decrypted_mnemonic = CIPHER.decrypt(wallet.encrypted_private_key.encode('utf-8')).decode('utf-8')
        mnemonic_list = decrypted_mnemonic.split()
        ton_wallet, _, _, _ = WalletV4R2.from_mnemonic(client, mnemonic_list)

        wallet_balance_before = await client.get_account_balance(ton_wallet.address.to_str())
        logger.info(f"Wallet balance before swap: {wallet_balance_before} nanoTON")

        offer_amount = to_nano(amount_ton, DECIMALS)
        gas_buffer = to_nano(0.01, DECIMALS)  # 0.01 TON gas buffer

        if offer_amount + gas_buffer > wallet_balance_before:
            raise ValueError("Insufficient TON balance to cover the swap and gas fees.")

        router_address = await get_router_address(token_mint, amount_ton, slippage_bps)
        router = StonfiRouterV2(client, router_address=Address(router_address))

        min_amount_out = int(offer_amount * (1 - slippage_bps / 10000))

        try:
            to, value, body = await router.get_swap_ton_to_jetton_tx_params(
                user_wallet_address=ton_wallet.address,
                receiver_address=ton_wallet.address,
                offer_jetton_address=Address(token_mint),
                offer_amount=offer_amount,
                min_ask_amount=min_amount_out,
                refund_address=ton_wallet.address,
            )
        except Exception as e:
            logger.error(f"Failed to fetch swap parameters: {str(e)}", exc_info=True)
            return {"error": "Failed to fetch swap parameters"}

        try:
            tx_hash = await ton_wallet.transfer(
                destination=to,
                amount=to_amount(value),
                body=body,
            )
            logger.info(f"TON swap transaction sent: {tx_hash}")
        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}", exc_info=True)
            return {"error": "Transaction failed"}

        # Verify transaction status
        try:
            transactions = await client.get_transactions(ton_wallet.address.to_str())
            tx_info = next((tx for tx in transactions if tx["hash"] == tx_hash), None)

            if not tx_info:
                 raise ValueError(f"Transaction not found: {tx_hash}")
            if not tx_info.get("success", False):
                raise ValueError(f"Transaction failed: {tx_info}")

            logger.info(f"Transaction successful: {tx_info}")
        except Exception as e:
             logger.error(f"Failed to verify transaction: {str(e)}", exc_info=True)
             return {"error": "Failed to verify transaction"}

        wallet_balance_after = await client.get_account_balance(ton_wallet.address.to_str())
        logger.info(f"Wallet balance after swap: {wallet_balance_after} nanoTON")

        gas_used = wallet_balance_before - wallet_balance_after - offer_amount
        logger.info(f"Gas fees used: {gas_used} nanoTON")

        return {"output_amount": min_amount_out, "tx_id": tx_hash}

    except ValueError as ve:
        logger.error(f"ValueError: {ve}")
        return {"error": str(ve)}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {"error": "Unexpected error occurred"}


async def get_router_address(token_mint: str, amount_ton: float, slippage_bps: int) -> str:
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

                min_ask_units = content.get("min_ask_units")
                ask_units = content.get("ask_units")
                logger.info(f"Expected Output (min_ask_units): {min_ask_units}")
                logger.info(f"Actual Output (ask_units): {ask_units}")

                return router_address
            else:
                error_text = await response.text()
                logger.error(f"Failed to get router address. Status: {response.status}, Error: {error_text}")
                raise Exception(f"Failed to get router address: {response.status}: {error_text}")
