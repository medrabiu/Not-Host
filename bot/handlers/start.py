import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database.db import get_async_session, get_user, add_user
from services.wallet_management import create_user_wallet, get_wallet
from services.utils import get_wallet_balance_and_usd  # Import new utility
logger = logging.getLogger(__name__)

# Updated trading menu (aligned with main.py)
TRADING_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("🟩 Buy", callback_data="buy"),
     InlineKeyboardButton("🟥 Sell", callback_data="sell")],
    [InlineKeyboardButton("Positions", callback_data="positions"),
     InlineKeyboardButton("Token List", callback_data="token_list")],
    [InlineKeyboardButton("P&L", callback_data="pnl"),
     InlineKeyboardButton("Orders", callback_data="orders")],
    [InlineKeyboardButton("Wallet", callback_data="wallet"),
     InlineKeyboardButton("Settings", callback_data="settings"),
     InlineKeyboardButton("Feedback", callback_data="feedback")],
    [InlineKeyboardButton("Help", callback_data="help")]
])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command, onboard new users or greet returning ones.

    New Users: Welcome message -> Agree -> Wallet setup -> Trading menu.
    Returning Users: Direct to trading menu with wallet info.
    """
    try:
        user = update.effective_user
        if not user:
            logger.error("No user info available in update")
            await update.message.reply_text("Oops! Something went wrong. Try again later.")
            return

        if context.user_data.get("last_start") == update.message.message_id:
            logger.info(f"Duplicate /start from {user.id}")
            return
        context.user_data["last_start"] = update.message.message_id

        telegram_id = str(user.id)
        async with await get_async_session() as session:
            db_user = await get_user(telegram_id, session)
            if not db_user:
                # New user: Add to DB and show welcome message with Agree button
                await add_user(telegram_id, session)
                await session.commit()
                welcome_msg = (
                    "👋 *Welcome to Not-Cotrader!*\n\n"
                    "Your multi-chain trading companion for lightning-fast trades on TON and Solana.\n"
                    "Swap tokens, track positions, and manage wallets—all in one place.\n\n"
                    "By clicking \"Agree and Continue\", you accept our terms and conditions."
                )
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Agree and Continue", callback_data="agree")]
                ])
                await update.message.reply_text(welcome_msg, reply_markup=keyboard, parse_mode="Markdown")
                logger.info(f"Sent welcome message to new user {telegram_id}")
            else:
                # Returning user: Show trading interface with wallet info and balances
                sol_wallet = await get_wallet(telegram_id, "solana", session)
                ton_wallet = await get_wallet(telegram_id, "ton", session)
                sol_address = sol_wallet.public_key if sol_wallet else "Not set"
                ton_address = ton_wallet.public_key if ton_wallet else "Not set"

                # Fetch balances and USD values
                sol_balance, sol_usd = await get_wallet_balance_and_usd(sol_address, "solana") if sol_wallet else (0.0, 0.0)
                ton_balance, ton_usd = await get_wallet_balance_and_usd(ton_address, "ton") if ton_wallet else (0.0, 0.0)

                trading_msg = (
                    "🔄 *Not-Cotrader*\n\n"
                    f"💧 *Sol-Wallet*: {sol_balance:.4f} SOL (${sol_usd:.2f})\n`{sol_address}`\n(tap to copy)\n\n"
                    f"💎 *TON-Wallet*: {ton_balance:.4f} TON (${ton_usd:.2f})\n`{ton_address}`\n(tap to copy)\n\n"
                    "Start trading by typing a mint/contract address or use the menu below:"
                )
                await update.message.reply_text(trading_msg, reply_markup=TRADING_MENU, parse_mode="Markdown")
                logger.info(f"Displayed trading interface for returning user {telegram_id}")

    except Exception as e:
        logger.error(f"Error in start handler: {str(e)}", exc_info=True)
        await update.message.reply_text("An error occurred. Please try again.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from start flow."""
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)

    if query.data == "agree":
        # New user agrees: Create wallets and show setup options
        async with await get_async_session() as session:
            sol_wallet = await get_wallet(user_id, "solana", session)
            if not sol_wallet:
                sol_wallet = await create_user_wallet(user_id, "solana", session)
                await session.commit()
            ton_wallet = await get_wallet(user_id, "ton", session)
            if not ton_wallet:
                ton_wallet = await create_user_wallet(user_id, "ton", session)
                await session.commit()

            # Fetch balances and USD values
            sol_balance, sol_usd = await get_wallet_balance_and_usd(sol_wallet.public_key, "solana")
            ton_balance, ton_usd = await get_wallet_balance_and_usd(ton_wallet.public_key, "ton")

            setup_msg = (
                "🔑 *Your Trading Wallets Are Ready!*\n\n"
                f"💧 *Sol-Wallet*: {sol_balance:.4f} SOL (${sol_usd:.2f})\n`{sol_wallet.public_key}`\n(tap to copy)\n\n"
                f"💎 *TON-Wallet*: {ton_balance:.4f} TON (${ton_usd:.2f})\n`{ton_wallet.public_key}`\n(tap to copy)\n\n"
                "💸 *Deposit*: Send funds directly to these addresses (tap to copy).\n"
                "🔄 *Import*: Use an existing wallet if you have one.\n"
                "⬆️ *TON Connect*: Top up TON via your main wallet."
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
                 InlineKeyboardButton("Import Wallet", callback_data="import_wallet"),
                 InlineKeyboardButton("TON Connect Topup", url=f"ton://transfer/{ton_wallet.public_key}?amount=0")]
            ])
            await query.edit_message_text(setup_msg, reply_markup=keyboard, parse_mode="Markdown")
            logger.info(f"Displayed wallet setup for user {user_id}")

    elif query.data in ["main_menu", "import_wallet"]:
        # After Main Menu or Import: Show trading interface
        async with await get_async_session() as session:
            sol_wallet = await get_wallet(user_id, "solana", session)
            ton_wallet = await get_wallet(user_id, "ton", session)
            sol_address = sol_wallet.public_key if sol_wallet else "Not set"
            ton_address = ton_wallet.public_key if ton_wallet else "Not set"

            # Fetch balances and USD values
            sol_balance, sol_usd = await get_wallet_balance_and_usd(sol_address, "solana") if sol_wallet else (0.0, 0.0)
            ton_balance, ton_usd = await get_wallet_balance_and_usd(ton_address, "ton") if ton_wallet else (0.0, 0.0)

            trading_msg = (
                "🔄 *Not-Cotrader*\n\n"
                f"💧 *Sol-Wallet*: {sol_balance:.4f} SOL (${sol_usd:.2f})\n`{sol_address}`\n(tap to copy)\n\n"
                f"💎 *TON-Wallet*: {ton_balance:.4f} TON (${ton_usd:.2f})\n`{ton_address}`\n(tap to copy)\n\n"
                "Start trading by typing a mint/contract address or use the menu below:"
            )
            await query.edit_message_text(trading_msg, reply_markup=TRADING_MENU, parse_mode="Markdown")
            logger.info(f"Displayed trading interface for user {user_id} after {query.data}")

            # Stub for import_wallet
            if query.data == "import_wallet":
                logger.info(f"User {user_id} clicked Import Wallet - stubbed for now")

# Export handlers
start_handler = CommandHandler("start", start)
start_callback_handler = CallbackQueryHandler(handle_callback, pattern="^(agree|main_menu|import_wallet)$")