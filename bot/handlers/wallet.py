import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes
from database.db import get_async_session
from services.wallet_management import get_wallet
from services.utils import get_wallet_balance_and_usd
from bot.handlers.common import refresh_handler, main_menu_handler, add_common_buttons

logger = logging.getLogger(__name__)

# Main wallet menu
WALLET_MAIN_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("Solana Wallet", callback_data="solana_wallet"),
     InlineKeyboardButton("TON Wallet", callback_data="ton_wallet")]
])

# Detailed wallet menu (shared for SOL and TON)
def get_detailed_wallet_menu(chain: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Wallet Reset", callback_data=f"reset_{chain}_wallet"),
         InlineKeyboardButton("Export Wallet", callback_data=f"export_{chain}_wallet")],
        [InlineKeyboardButton("Import Wallet", callback_data=f"import_{chain}_wallet"),
         InlineKeyboardButton(f"Withdraw All {chain.upper()}", callback_data=f"withdraw_all_{chain}")],
        [InlineKeyboardButton(f"Withdraw X {chain.upper()}", callback_data=f"withdraw_x_{chain}")]
    ]
    return add_common_buttons(keyboard, chain)  # Add Refresh and Main Menu

async def wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the 'Wallet' button click from the main menu."""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    async with get_async_session() as session:
        sol_wallet = await get_wallet(user_id, "solana", session)
        ton_wallet = await get_wallet(user_id, "ton", session)
        sol_address = sol_wallet.public_key if sol_wallet else "Not set"
        ton_address = ton_wallet.public_key if ton_wallet else "Not set"

    msg = (
        "Your Wallets:\n"
        f"🔹 Solana: `{sol_address}`\n"
        f"🔸 TON: `{ton_address}`\n"
        "Select an option below:"
    )
    await query.edit_message_text(msg, reply_markup=WALLET_MAIN_MENU, parse_mode="Markdown")
    logger.info(f"Displayed wallet overview for user {user_id}")

async def detailed_wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle detailed wallet view for Solana or TON."""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    chain = "solana" if "solana" in query.data else "ton"
    chain_display = "Solana" if chain == "solana" else "TON"
    chain_unit = "SOL" if chain == "solana" else "TON"

    async with get_async_session() as session:
        wallet = await get_wallet(user_id, chain, session)
        address = wallet.public_key if wallet else "Not set"
        balance, usd_value = await get_wallet_balance_and_usd(address, chain) if wallet else (0.0, 0.0)

    msg = (
        f"{chain_display} Wallet:\n"
        f"Address: `{address}`\n"
        f"Balance: {balance:.2f} {chain_unit} (${usd_value:.2f})\n\n"
        "Import wallet if you already have one."
    )
    await query.edit_message_text(msg, reply_markup=get_detailed_wallet_menu(chain), parse_mode="Markdown")
    logger.info(f"Displayed {chain_display} wallet details for user {user_id}")

# Stubs for additional functionalities
async def reset_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chain = "solana" if "solana" in query.data else "ton"
    await query.edit_message_text(f"Resetting {chain} wallet - feature coming soon!", parse_mode="Markdown")
    logger.info(f"User {update.effective_user.id} requested {chain} wallet reset - stubbed")

async def export_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chain = "solana" if "solana" in query.data else "ton"
    await query.edit_message_text(f"Exporting {chain} wallet - feature coming soon!", parse_mode="Markdown")
    logger.info(f"User {update.effective_user.id} requested {chain} wallet export - stubbed")

async def import_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chain = "solana" if "solana" in query.data else "ton"
    await query.edit_message_text(f"Importing {chain} wallet - feature coming soon!", parse_mode="Markdown")
    logger.info(f"User {update.effective_user.id} requested {chain} wallet import - stubbed")

async def withdraw_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chain = "solana" if "solana" in query.data else "ton"
    chain_unit = "SOL" if chain == "solana" else "TON"
    await query.edit_message_text(f"Withdrawing all {chain_unit} - feature coming soon!", parse_mode="Markdown")
    logger.info(f"User {update.effective_user.id} requested withdraw all {chain_unit} - stubbed")

async def withdraw_x(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chain = "solana" if "solana" in query.data else "ton"
    chain_unit = "SOL" if chain == "solana" else "TON"
    await query.edit_message_text(f"Withdrawing X {chain_unit} - feature coming soon!", parse_mode="Markdown")
    logger.info(f"User {update.effective_user.id} requested withdraw X {chain_unit} - stubbed")

# Export handlers
wallet_handler = CallbackQueryHandler(wallet_handler, pattern="^wallet$")
wallet_callbacks = [
    CallbackQueryHandler(detailed_wallet_handler, pattern="^(solana_wallet|ton_wallet)$"),
    CallbackQueryHandler(lambda update, context: refresh_handler(update, context, update.callback_query.data, detailed_wallet_handler), 
                         pattern="^refresh_(solana|ton)_wallet$"),
    CallbackQueryHandler(reset_wallet, pattern="^reset_(solana|ton)_wallet$"),
    CallbackQueryHandler(export_wallet, pattern="^export_(solana|ton)_wallet$"),
    CallbackQueryHandler(import_wallet, pattern="^import_(solana|ton)_wallet$"),
    CallbackQueryHandler(withdraw_all, pattern="^withdraw_all_(solana|ton)$"),
    CallbackQueryHandler(withdraw_x, pattern="^withdraw_x_(solana|ton)$"),
    CallbackQueryHandler(main_menu_handler, pattern="^main_menu$")  # Use reusable main_menu_handler
]