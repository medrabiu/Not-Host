import logging
import aiohttp
from pytoniq_core import Address
from tonutils.client import TonapiClient
from tonutils.jetton.dex.stonfi import StonfiRouterV2
from tonutils.jetton.dex.stonfi.v2.pton.constants import PTONAddresses
from tonutils.utils import to_nano, to_amount
from tonutils.wallet import WalletV4R2
from services.crypto import CIPHER
from typing import Dict
import os

logger = logging.getLogger(__name__)

# Configs
API_KEY = os.getenv("TON_API_KEY", "AGVENPU5U7V6FDQAAAAEOR3JTJPI7Q7EFPHIOEUOEVVEHZ452BPDMPC2JCBNKBBWTJMHCBI")
IS_TESTNET = os.getenv("IS_TESTNET", "False") == "True"
JETTON_DECIMALS = 9  # Assuming 9 decimals for the jetton (e.g., USD₮), adjust if needed
DEFAULT_SLIPPAGE_BPS = 50  # Default 0.5% slippage

def nano_to_units(nano_amount: int, decimals: int) -> float:
    """Convert nano units to human-readable units (TON or jetton)."""
    return nano_amount / 10**decimals

async def get_router_address(from_jetton_address: str, jetton_amount: float, slippage_bps: int) -> str:
    """Fetch the router address for a jetton-to-TON swap using STON.fi API."""
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
                logger.info(f"Expected TON output: {nano_to_units(int(ask_units), 9) if ask_units != 'N/A' else 'N/A':.9f} TON, "
                            f"Min expected: {nano_to_units(int(min_ask_units), 9) if min_ask_units != 'N/A' else 'N/A':.9f} TON")
                return router_address
            else:
                error_text = await response.text()
                logger.error(f"Failed to get router address. Status: {response.status}, Error: {error_text}")
                raise Exception(f"Failed to get router address: {response.status}: {error_text}")

async def execute_jetton_to_ton_swap(wallet, from_jetton_address: str, jetton_amount: float, slippage_bps: int = DEFAULT_SLIPPAGE_BPS) -> Dict:
    """
    Execute a jetton-to-TON swap on STON.fi DEX (V2) with slippage and gas fee tracking.
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

        # Fetch TON balance before swap (for gas fees)
        ton_balance_before = await client.get_account_balance(ton_wallet.address.to_str())
        logger.info(f"TON balance before swap: {nano_to_units(ton_balance_before, 9):.9f} TON ({ton_balance_before} nanoTON)")

        router_address = await get_router_address(from_jetton_address, jetton_amount, slippage_bps)
        router = StonfiRouterV2(client, router_address=Address(router_address))

        offer_amount = to_nano(jetton_amount, JETTON_DECIMALS)
        min_ask_amount = int(offer_amount * (1 - slippage_bps / 10000))  # Minimum TON output after slippage
        logger.info(f"Offer amount: {nano_to_units(offer_amount, JETTON_DECIMALS):.9f} jettons ({offer_amount} nanoJettons), "
                    f"Min TON output: {nano_to_units(min_ask_amount, 9):.9f} TON ({min_ask_amount} nanoTON)")

        to, value, body = await router.get_swap_jetton_to_ton_tx_params(
            offer_jetton_address=Address(from_jetton_address),
            receiver_address=ton_wallet.address,
            user_wallet_address=ton_wallet.address,
            offer_amount=offer_amount,
            min_ask_amount=min_ask_amount,
            refund_address=ton_wallet.address,
        )

        # Check if TON balance covers gas fees
        if value > ton_balance_before:
            wallet_address = ton_wallet.address.to_str(is_bounceable=False)
            raise ValueError(f"Insufficient TON for gas fees: {nano_to_units(value, 9):.9f} TON required, "
                            f"{nano_to_units(ton_balance_before, 9):.9f} TON available. "
                            f"Please fund your wallet to continue: {wallet_address}")

        tx_hash = await ton_wallet.transfer(
            destination=to,
            amount=to_amount(value),
            body=body,
        )
        logger.info(f"Jetton-to-TON swap transaction sent via STON.fi (V2): {tx_hash}")

        ton_balance_after = await client.get_account_balance(ton_wallet.address.to_str())
        logger.info(f"TON balance after swap: {nano_to_units(ton_balance_after, 9):.9f} TON ({ton_balance_after} nanoTON)")

        # Calculate gas fees (TON spent, not including jetton deduction)
        gas_fees_used = ton_balance_before - ton_balance_after
        logger.info(f"Gas fees used: {nano_to_units(gas_fees_used, 9):.9f} TON ({gas_fees_used} nanoTON)")

        return {"tx_id": tx_hash, "gas_fees_used": gas_fees_used}

    except Exception as e:
        logger.error(f"Failed to execute jetton-to-TON swap: {str(e)}", exc_info=True)
        raise
