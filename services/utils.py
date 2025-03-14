import logging
import os
from blockchain.solana.utils import get_sol_balance, get_sol_price
from blockchain.ton.utils import get_ton_balance, get_ton_price
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db import get_async_session
from services.wallet_management import get_wallet
import aiohttp
from solana.rpc.async_api import AsyncClient as SolanaAsyncClient
from spl.token.constants import TOKEN_PROGRAM_ID
from solders.pubkey import Pubkey

logger = logging.getLogger(__name__)

TON_API_KEY = os.getenv("TON_API_KEY", "AGVENPU5U7V6FDQAAAAEOR3JTJPI7Q7EFPHIOEUOEVVEHZ452BPDMPC2JCBNKBBWTJMHCBI")
IS_TESTNET = os.getenv("IS_TESTNET", "False") == "True"
SOLANA_RPC_ENDPOINT = "https://api.mainnet-beta.solana.com"  # Adjust for testnet if needed


async def get_wallet_balance_and_usd(wallet_address: str, chain: str) -> tuple[float, float]:
    """
    Get the balance and USD equivalent for a wallet address on a specified chain.

    This function retrieves the native token balance and its USD value for a given
    wallet address on either the Solana or TON blockchain.

    Args:
        wallet_address (str): The wallet address to query.
        chain (str): The blockchain to use ('solana' or 'ton').

    Returns:
        tuple[float, float]: A tuple containing:
            - balance (float): The native token balance (SOL or TON).
            - usd_value (float): The equivalent value in USD.

        Returns (0.0, 0.0) if the chain is unsupported or an error occurs.

    Raises:
        Exception: If balance or price retrieval fails (caught and logged).
    """
    try:
        if chain.lower() == "solana":
            balance = await get_sol_balance(wallet_address)
            price = await get_sol_price()
        elif chain.lower() == "ton":
            balance = await get_ton_balance(wallet_address)
            price = await get_ton_price()
        else:
            logger.error(f"Unsupported chain: {chain}")
            return 0.0, 0.0

        usd_value = balance * price
        logger.info(f"Calculated USD value for {wallet_address} on {chain}: ${usd_value}")
        return balance, usd_value
    except Exception as e:
        logger.error(f"Error in get_wallet_balance_and_usd for {wallet_address}: {str(e)}")
        return 0.0, 0.0

async def get_token_balance(public_key: str, token_address: str, chain: str) -> float:
    """
    Fetch the token balance for a given wallet address and token on a specified chain.

    Args:
        public_key (str): The wallet address to query (Solana public key or TON address).
        token_address (str): The token contract address (SPL token mint or jetton master address).
        chain (str): The blockchain to use ('solana' or 'ton').

    Returns:
        float: The token balance in human-readable units (e.g., 1.5 USDT).

    Raises:
        Exception: If balance retrieval fails (caught and logged, returns 0.0).
    """
    try:
        if chain.lower() == "solana":
            # Solana SPL token balance
            async with SolanaAsyncClient(SOLANA_RPC_ENDPOINT) as client:
                # Get the token account address (Associated Token Account)
                token_mint = Pubkey(token_address)
                wallet_pubkey = Pubkey(public_key)
                ata = Pubkey.find_program_address(
                    [bytes(wallet_pubkey), bytes(TOKEN_PROGRAM_ID), bytes(token_mint)],
                    TOKEN_PROGRAM_ID
                )[0]

                # Fetch token account balance
                response = await client.get_token_account_balance(ata)
                if "result" in response and "value" in response["result"]:
                    amount = int(response["result"]["value"]["amount"])
                    decimals = int(response["result"]["value"]["decimals"])
                    balance = amount / 10**decimals
                    logger.info(f"Solana token balance for {public_key} ({token_address}): {balance}")
                    return balance
                else:
                    logger.warning(f"No token account found for {public_key} with mint {token_address}")
                    return 0.0

        elif chain.lower() == "ton":
            # TON jetton balance via TonAPI
            url = f"https://{'testnet.' if IS_TESTNET else ''}tonapi.io/v2/accounts/{public_key}/jettons/{token_address}"
            headers = {"Authorization": f"Bearer {TON_API_KEY}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        balance_nano = int(data.get("balance", 0))  # Nano units
                        # Fetch jetton decimals (assuming 9 if not provided; ideally fetch from contract)
                        decimals = 9  # Adjust if you have a way to fetch this dynamically
                        balance = balance_nano / 10**decimals
                        logger.info(f"TON jetton balance for {public_key} ({token_address}): {balance}")
                        return balance
                    else:
                        logger.error(f"Failed to fetch TON jetton balance: {response.status}, {await response.text()}")
                        return 0.0
        else:
            logger.error(f"Unsupported chain for token balance: {chain}")
            return 0.0
    except Exception as e:
        logger.error(f"Error fetching token balance for {public_key} on {chain}: {str(e)}")
        return 0.0

async def refresh_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str, prev_message_func: callable) -> None:
    """
    Reusable handler to refresh and re-display the previous view if details changed.

    This function answers a callback query, re-runs the previous message function,
    and updates the Telegram message only if the content or markup has changed.

    Args:
        update (Update): The Telegram update object containing the callback query.
        context (ContextTypes.DEFAULT_TYPE): The Telegram context object.
        callback_data (str): The callback data identifier for storing/retrieving message data.
        prev_message_func (callable): The function to re-run to generate the updated view.

    Returns:
        None

    Notes:
        - Uses context.user_data to store and compare old/new message content and markup.
        - Logs whether an update was skipped or applied.
    """
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)

    old_msg = context.user_data.get(f"last_{callback_data}_msg", "")
    old_markup = context.user_data.get(f"last_{callback_data}_markup", None)

    await prev_message_func(update, context)

    new_msg = context.user_data.get(f"last_{callback_data}_msg", "")
    new_markup = context.user_data.get(f"last_{callback_data}_markup", None)

    if old_msg == new_msg and old_markup == new_markup:
        logger.debug(f"No changes detected for {callback_data} - skipping update for user {user_id}")
    else:
        await query.edit_message_text(new_msg, reply_markup=new_markup, parse_mode="Markdown")
        logger.info(f"Refreshed view for user {user_id} with callback: {callback_data}")

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Reusable handler to return to the TRADING_MENU.

    This function answers a callback query, retrieves wallet details and balances
    for Solana and TON, and updates the Telegram message with the main trading menu.

    Args:
        update (Update): The Telegram update object containing the callback query.
        context (ContextTypes.DEFAULT_TYPE): The Telegram context object.

    Returns:
        None

    Notes:
        - Fetches wallet addresses and balances from the database and blockchain utils.
        - Displays 'Not set' for wallets not configured by the user.
        - Uses Markdown formatting for the message with clickable addresses.
    """
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)

    async with await get_async_session() as session:
        sol_wallet = await get_wallet(user_id, "solana", session)
        ton_wallet = await get_wallet(user_id, "ton", session)
        sol_address = sol_wallet.public_key if sol_wallet else "Not set"
        ton_address = ton_wallet.public_key if ton_wallet else "Not set"
        sol_balance, sol_usd = await get_wallet_balance_and_usd(sol_address, "solana") if sol_wallet else (0.0, 0.0)
        ton_balance, ton_usd = await get_wallet_balance_and_usd(ton_address, "ton") if ton_wallet else (0.0, 0.0)

    from bot.handlers.start import TRADING_MENU
    msg = (
        "Not-Cotrader\n\n"
        f"Sol-Wallet: {sol_balance:.2f} SOL (${sol_usd:.2f})\n`{sol_address}`\n(tap to copy)\n\n"
        f"TON-Wallet: {ton_balance:.2f} TON (${ton_usd:.2f})\n`{ton_address}`\n(tap to copy)\n\n"
        "Start trading by typing a mint/contract address"
    )
    await query.edit_message_text(msg, reply_markup=TRADING_MENU, parse_mode="Markdown")
    logger.info(f"Returned to TRADING_MENU for user {user_id}")

def add_common_buttons(keyboard: list, callback_data: str) -> InlineKeyboardMarkup:
    """
    Add reusable 'Refresh' and 'Main Menu' buttons to an existing keyboard.

    This function prepends a row of common buttons to the provided keyboard list
    and returns an InlineKeyboardMarkup object.

    Args:
        keyboard (list): The existing list of keyboard rows to modify.
        callback_data (str): The callback data identifier to prefix the 'Refresh' button.

    Returns:
        InlineKeyboardMarkup: The updated keyboard markup with added buttons.
    """
    common_buttons = [
        InlineKeyboardButton("Refresh", callback_data=f"refresh_{callback_data}"),
        InlineKeyboardButton("Main Menu", callback_data="main_menu")
    ]
    keyboard.insert(0, common_buttons)
    return InlineKeyboardMarkup(keyboard)