import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database.db import get_async_session, get_user, add_user
from services.wallet_management import create_user_wallet, get_wallet

logger = logging.getLogger(__name__)

# Trading menu for new and returning users
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
        session = await get_async_session()
        try:
            db_user = await get_user(telegram_id, session)
            if not db_user:
                # New user: Add to DB and show welcome message with Agree button
                await add_user(telegram_id, session)
                await session.commit()  # Commit the user to the DB
                welcome_msg = (
                    "Welcome to Not-Cotrader!\n"
                    "Not-Cotrader is your Multichain trading bud, built for lightning-fast trades "
                    "on Solana and TON.\n\n"
                    "By tapping \" Agree and Continue\", you agree to the terms and conditions."
                )
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(" Agree and Continue", callback_data="agree")]
                ])
                await update.message.reply_text(welcome_msg, reply_markup=keyboard)
                logger.info(f"Sent welcome message to new user {telegram_id}")
            else:
                # Returning user: Show trading interface with wallet info
                sol_wallet = await get_wallet(telegram_id, "solana", session)
                ton_wallet = await get_wallet(telegram_id, "ton", session)
                sol_address = sol_wallet.public_key if sol_wallet else "Not set"
                ton_address = ton_wallet.public_key if ton_wallet else "Not set"

                trading_msg = (
                    "Not-Cotrader\n\n"
                    f"Sol-Wallet\n`{sol_address}`\n(tap to copy)\n\n"
                    f"TON-Wallet\n`{ton_address}`\n(tap to copy)\n\n"
                    "Start trading by typing a mint/contract address"
                )
                await update.message.reply_text(trading_msg, reply_markup=TRADING_MENU, parse_mode="Markdown")
                logger.info(f"Displayed trading interface for returning user {telegram_id}")
        finally:
            await session.close()

    except Exception as e:
        logger.error(f"Error in start handler: {str(e)}")
        await update.message.reply_text("An error occurred. Please try again.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from start flow."""
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)

    if query.data == "agree":
        # New user agrees: Create wallets and show setup options
        session = await get_async_session()
        try:
            sol_wallet = await get_wallet(user_id, "solana", session)
            if not sol_wallet:
                sol_wallet = await create_user_wallet(user_id, "solana", session)
                await session.commit()
            ton_wallet = await get_wallet(user_id, "ton", session)
            if not ton_wallet:
                ton_wallet = await create_user_wallet(user_id, "ton", session)
                await session.commit()

            setup_msg = (
                "Here are your trading bot wallets:\n\n"
                f"Sol-Wallet\n`{sol_wallet.public_key}`\n(tap to copy)\n\n"
                f"TON-Wallet\n`{ton_wallet.public_key}`\n(tap to copy)\n\n"
                "$ Deposit directly -> tap the wallet address to copy\n\n"
                "Import wallet if you already have one\n\n"
                "Tap TON Connect to top up from your main TON wallet"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Skip", callback_data="skip"),
                 InlineKeyboardButton("Import Wallet", callback_data="import_wallet"),
                 InlineKeyboardButton("TON Connect Topup", url=f"ton://transfer/{ton_wallet.public_key}?amount=0")]
            ])
            await query.edit_message_text(setup_msg, reply_markup=keyboard, parse_mode="Markdown")
            logger.info(f"Displayed wallet setup for user {user_id}")

        finally:
            await session.close()

    elif query.data in ["skip", "import_wallet"]:
        # After Skip or Import: Show trading interface
        session = await get_async_session()
        try:
            sol_wallet = await get_wallet(user_id, "solana", session)
            ton_wallet = await get_wallet(user_id, "ton", session)
            sol_address = sol_wallet.public_key if sol_wallet else "Not set"
            ton_address = ton_wallet.public_key if ton_wallet else "Not set"

            trading_msg = (
                "Not-Cotrader\n\n"
                f"Sol-Wallet\n`{sol_address}`\n(tap to copy)\n\n"
                f"TON-Wallet\n`{ton_address}`\n(tap to copy)\n\n"
                "Start trading by typing a mint/contract address"
            )
            await query.edit_message_text(trading_msg, reply_markup=TRADING_MENU, parse_mode="Markdown")
            logger.info(f"Displayed trading interface for user {user_id} after {query.data}")

            # Stub for import_wallet (no action yet)
            if query.data == "import_wallet":
                logger.info(f"User {user_id} clicked Import Wallet - stubbed for now")

        finally:
            await session.close()

# Export handlers
start_handler = CommandHandler("start", start)
start_callback_handler = CallbackQueryHandler(handle_callback, pattern="^(agree|skip|import_wallet)$")