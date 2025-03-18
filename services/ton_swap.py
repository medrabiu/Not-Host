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
JETTON_DECIMALS = 9  # Assuming 9 decimals for jettons, adjust if specific tokens differ
DEFAULT_SLIPPAGE_BPS = 50

def nano_to_units(nano_amount: int, decimals: int = DECIMALS) -> float:
    """Convert nano units to human-readable units (TON or jetton)."""
    return nano_amount / 10**decimals

async def get_router_address_buy(token_mint: str, amount_ton: float, slippage_bps: int) -> str:
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
    logger.info(f"Fetching buy router address with params: {params}")
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params, headers=headers) as response:
            if response.status == 200:
                content = await response.json()
                logger.info(f"STON.fi simulation response: {content}")
                router_address = content.get("router_address")
                if not router_address:
                    raise ValueError("Router address not found in API response.")
                return router_address
            else:
                error_text = await response.text()
                logger.error(f"Failed to get buy router address: {response.status}, {error_text}")
                raise Exception(f"Failed to get router address: {response.status}: {error_text}")

async def get_router_address_sell(from_jetton_address: str, jetton_amount: float, slippage_bps: int) -> str:
    url = "https://api.ston.fi/v1/swap/simulate"
    headers = {"Accept": "application/json"}
    slippage_tolerance = slippage_bps / 100
    params = {
        "offer_address": from_jetton_address,
        "ask_address": PTONAddresses.TESTNET if IS_TESTNET else PTONAddresses.MAINNET,
        "units": to_nano(jetton_amount, JETTON_DECIMALS),
        "slippage_tolerance": slippage_tolerance,
        "dex_v2": "true",
    }
    logger.info(f"Fetching sell router address with params: {params}")
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params, headers=headers) as response:
            if response.status == 200:
                content = await response.json()
                logger.info(f"STON.fi simulation response: {content}")
                router_address = content.get("router_address")
                if not router_address:
                    raise ValueError("Router address not found in API response.")
                return router_address
            else:
                error_text = await response.text()
                logger.error(f"Failed to get sell router address: {response.status}, {error_text}")
                raise Exception(f"Failed to get router address: {response.status}: {error_text}")

async def execute_ton_swap(wallet, token_mint: str, amount_ton: float, slippage_bps: int = DEFAULT_SLIPPAGE_BPS) -> Dict:
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
        logger.info(f"Wallet balance before buy: {nano_to_units(wallet_balance_before):.9f} TON")

        router_address = await get_router_address_buy(token_mint, amount_ton, slippage_bps)
        router = StonfiRouterV2(client, router_address=Address(router_address))

        offer_amount = to_nano(amount_ton, DECIMALS)
        min_ask_amount = int(offer_amount * (1 - slippage_bps / 10000))
        to, value, body = await router.get_swap_ton_to_jetton_tx_params(
            user_wallet_address=ton_wallet.address,
            receiver_address=ton_wallet.address,
            offer_jetton_address=Address(token_mint),
            offer_amount=offer_amount,
            min_ask_amount=min_ask_amount,
            refund_address=ton_wallet.address,
        )

        if value > wallet_balance_before:
            wallet_address = ton_wallet.address.to_str(is_bounceable=False)
            raise ValueError(f"Insufficient TON: {nano_to_units(value):.9f} TON needed, "
                            f"{nano_to_units(wallet_balance_before):.9f} TON available. Fund: {wallet_address}")

        tx_hash = await ton_wallet.transfer(
            destination=to,
            amount=to_amount(value),
            body=body,
        )
        logger.info(f"TON buy transaction sent: {tx_hash}")

        wallet_balance_after = await client.get_account_balance(ton_wallet.address.to_str())
        total_deducted = wallet_balance_before - wallet_balance_after
        gas_fees_used = total_deducted - offer_amount
        return {"tx_id": tx_hash, "gas_fees_used": gas_fees_used}

    except Exception as e:
        logger.error(f"Failed to execute TON buy: {str(e)}", exc_info=True)
        raise

async def execute_jetton_to_ton_swap(wallet, from_jetton_address: str, jetton_amount: float, slippage_bps: int = DEFAULT_SLIPPAGE_BPS) -> Dict:
    try:
        client = TonapiClient(api_key=API_KEY, is_testnet=IS_TESTNET)
        try:
            decrypted_mnemonic = CIPHER.decrypt(wallet.encrypted_private_key.encode('utf-8')).decode('utf-8')
            mnemonic_list = decrypted_mnemonic.split()
            ton_wallet, _, _, _ = WalletV4R2.from_mnemonic(client, mnemonic_list)
        except Exception as e:
            logger.error(f"Failed to decrypt mnemonic: {str(e)}")
            raise ValueError("Invalid encrypted mnemonic or decryption key")

        ton_balance_before = await client.get_account_balance(ton_wallet.address.to_str())
        logger.info(f"TON balance before sell: {nano_to_units(ton_balance_before):.9f} TON")

        router_address = await get_router_address_sell(from_jetton_address, jetton_amount, slippage_bps)
        router = StonfiRouterV2(client, router_address=Address(router_address))

        offer_amount = to_nano(jetton_amount, JETTON_DECIMALS)
        min_ask_amount = int(offer_amount * (1 - slippage_bps / 10000))
        to, value, body = await router.get_swap_jetton_to_ton_tx_params(
            offer_jetton_address=Address(from_jetton_address),
            receiver_address=ton_wallet.address,
            user_wallet_address=ton_wallet.address,
            offer_amount=offer_amount,
            min_ask_amount=min_ask_amount,
            refund_address=ton_wallet.address,
        )

        if value > ton_balance_before:
            wallet_address = ton_wallet.address.to_str(is_bounceable=False)
            raise ValueError(f"Insufficient TON for gas: {nano_to_units(value):.9f} TON needed, "
                            f"{nano_to_units(ton_balance_before):.9f} TON available. Fund: {wallet_address}")

        tx_hash = await ton_wallet.transfer(
            destination=to,
            amount=to_amount(value),
            body=body,
        )
        logger.info(f"Jetton-to-TON sell transaction sent: {tx_hash}")

        ton_balance_after = await client.get_account_balance(ton_wallet.address.to_str())
        gas_fees_used = ton_balance_before - ton_balance_after
        return {"tx_id": tx_hash, "gas_fees_used": gas_fees_used}

    except Exception as e:
        logger.error(f"Failed to execute jetton-to-TON sell: {str(e)}", exc_info=True)
        raise