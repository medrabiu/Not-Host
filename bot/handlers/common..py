import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db import get_async_session
from services.wallet_management import get_wallet
from services.utils import get_wallet_balance_and_usd
from bot.handlers.start import TRADING_MENU  # Import TRADING_MENU globally

logger = logging.getLogger(__name__)

async def refresh_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str, prev_message_func: callable) -> None:
    """
    Reusable handler to refresh and re-display the previous view.

    Args:
        update: Telegram update object.
        context: Context object with user data.
        callback_data: The original callback data triggering the refresh.
        prev_message_func: Function to regenerate the previous message (e.g., wallet or token details).
    """
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)

    # Re-run the previous message function to refresh data
    await prev_message_func(update, context)
    logger.info(f"Refreshed view for user {user_id} with callback: {callback_data}")

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reusable handler to return to the TRADING_MENU."""
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)

    async with get_async_session() as session:
        sol_wallet = await get_wallet(user_id, "solana", session)
        ton_wallet = await get_wallet(user_id, "ton", session)
        sol_address = sol_wallet.public_key if sol_wallet else "Not set"
        ton_address = ton_wallet.public_key if ton_wallet else "Not set"
        sol_balance, sol_usd = await get_wallet_balance_and_usd(sol_address, "solana") if sol_wallet else (0.0, 0.0)
        ton_balance, ton_usd = await get_wallet_balance_and_usd(ton_address, "ton") if ton_wallet else (0.0, 0.0)

    msg = (
        "Not-Cotrader\n\n"
        f"Sol-Wallet: {sol_balance:.2f} SOL (${sol_usd:.2f})\n`{sol_address}`\n(tap to copy)\n\n"
        f"TON-Wallet: {ton_balance:.2f} TON (${ton_usd:.2f})\n`{ton_address}`\n(tap to copy)\n\n"
        "Start trading by typing a mint/contract address"
    )
    await query.edit_message_text(msg, reply_markup=TRADING_MENU, parse_mode="Markdown")
    logger.info(f"Returned to TRADING_MENU for user {user_id}")

def add_common_buttons(keyboard: list, callback_data: str) -> InlineKeyboardMarkup:
    """Add reusable 'Refresh' and 'Main Menu' buttons to an existing keyboard."""
    common_buttons = [
        InlineKeyboardButton("Refresh", callback_data=f"refresh_{callback_data}"),
        InlineKeyboardButton("Main Menu", callback_data="main_menu")
    ]
    keyboard.insert(0, common_buttons)  # Add at the top
    return InlineKeyboardMarkup(keyboard)