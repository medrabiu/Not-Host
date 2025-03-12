import logging
import os
import aiohttp
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
API_KEY = os.getenv("TON_API_KEY", "AGVENPU5U7V6FDQAAAAEOR3JTJPI7Q7EFPHIOEUOEVVEHZ452BPDMPC2JCBNKBBWTJMHCBI")
IS_TESTNET = os.getenv("IS_TESTNET", "False") == "True"
DECIMALS = 9
DEFAULT_SLIPPAGE_BPS = 50

def nano_to_ton(nano_amount: int) -> float:
    """Convert nanoTON to TON for logging."""
    return nano_amount / 10**DECIMALS

async def get_router_address(token_mint: str, amount_ton: float, slippage_bps: int) -> str:
    url = "https://api.ston.fi/v1/swap/simulate"
    headers = {"Accept": "application/json"}
    slippage_tolerance = slippage_bps / 100
    params = {
        "offer_address": PTONAddresses.TESTNET if IS_TESTNET else PTONAddresses.MAINNET,
        "ask_address": token_mint,
        "units": to_nano(amount_ton, DECIMALS),
        "slippage_tolerance": slippage_tolerance,
        "dex_v2": "true",
    }
    logger.info(f"Fetching router address with params: {params}")
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params, headers=headers) as response:
            if response.status == 200:
                content = await response.json()
                logger.info(f"STON.fi simulation response: {content}")
                router_address = content.get("router_address")
                if not router_address:
                    raise ValueError("Router address not found in API response.")
                ask_units = content.get("ask_units", "N/A")
                min_ask_units = content.get("min_ask_units", "N/A")
                logger.info(f"Expected output: {ask_units} nanoTON, Min expected: {min_ask_units} nanoTON")
                return router_address
            else:
                error_text = await response.text()
                logger.error(f"Failed to get router address. Status: {response.status}, Error: {error_text}")
                raise Exception(f"Failed to get router address: {response.status}: {error_text}")

async def execute_ton_swap(wallet, token_mint: str, amount_ton: float, slippage_bps: int = DEFAULT_SLIPPAGE_BPS) -> Dict:
    """
    Execute a token swap on TON using STON.fi DEX (V2) with non-bounceable (UQ) address in logs.
    """
    try:
        client = TonapiClient(api_key=API_KEY, is_testnet=IS_TESTNET)
        try:
            decrypted_mnemonic = CIPHER.decrypt(wallet.encrypted_private_key.encode('utf-8')).decode('utf-8')
            mnemonic_list = decrypted_mnemonic.split()
            ton_wallet, _, _, _ = WalletV4R2.from_mnemonic(client, mnemonic_list)
        except Exception as e:
            logger.error(f"Failed to decrypt mnemonic: {str(e)}")
            raise ValueError("Invalid encrypted mnemonic or decryption key")

        wallet_balance_before = await client.get_account_balance(ton_wallet.address.to_str())
        logger.info(f"Wallet balance before swap: {nano_to_ton(wallet_balance_before):.9f} TON ({wallet_balance_before} nanoTON)")

        router_address = await get_router_address(token_mint, amount_ton, slippage_bps)
        router = StonfiRouterV2(client, router_address=Address(router_address))

        offer_amount = to_nano(amount_ton, DECIMALS)
        min_ask_amount = int(offer_amount * (1 - slippage_bps / 10000))
        logger.info(f"Offer amount: {nano_to_ton(offer_amount):.9f} TON ({offer_amount} nanoTON), "
                    f"Min ask amount: {nano_to_ton(min_ask_amount):.9f} TON ({min_ask_amount} nanoTON)")

        to, value, body = await router.get_swap_ton_to_jetton_tx_params(
            user_wallet_address=ton_wallet.address,
            receiver_address=ton_wallet.address,
            offer_jetton_address=Address(token_mint),
            offer_amount=offer_amount,
            min_ask_amount=min_ask_amount,
            refund_address=ton_wallet.address,
        )

        if value > wallet_balance_before:
            wallet_address = ton_wallet.address.to_str(is_bounceable=False)  # Use non-bounceable (UQ) format
            raise ValueError(f"Insufficient TON balance: {nano_to_ton(value):.9f} TON required, "
                            f"{nano_to_ton(wallet_balance_before):.9f} TON available. "
                            f"Please fund your wallet to continue: {wallet_address}")

        tx_hash = await ton_wallet.transfer(
            destination=to,
            amount=to_amount(value),
            body=body,
        )
        logger.info(f"TON swap transaction sent via STON.fi (V2): {tx_hash}")

        wallet_balance_after = await client.get_account_balance(ton_wallet.address.to_str())
        logger.info(f"Wallet balance after swap: {nano_to_ton(wallet_balance_after):.9f} TON ({wallet_balance_after} nanoTON)")

        total_deducted = wallet_balance_before - wallet_balance_after
        gas_fees_used = total_deducted - offer_amount
        logger.info(f"Total TON deducted: {nano_to_ton(total_deducted):.9f} TON ({total_deducted} nanoTON)")
        logger.info(f"Gas fees used: {nano_to_ton(gas_fees_used):.9f} TON ({gas_fees_used} nanoTON)")

        return {"tx_id": tx_hash, "gas_fees_used": gas_fees_used}

    except Exception as e:
        logger.error(f"Failed to execute TON swap: {str(e)}", exc_info=True)
        raise

