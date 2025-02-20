import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from database.db import get_session, get_user, add_user  # Import database utilities

# Configure logging for production debugging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token (move to config later)
TELEGRAM_TOKEN = "7754246943:AAFT82vJoG8g0zVb10HeSRfrhP6TSh0AyNM"

# Define main menu keyboard
MAIN_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("Buy", callback_data="buy"),
     InlineKeyboardButton("Sell", callback_data="sell")],
    [InlineKeyboardButton("Wallet", callback_data="wallet"),
     InlineKeyboardButton("Help", callback_data="help")]
])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command, register or greet user, and display the main menu.

    Edge Cases:
    - Handle database errors gracefully.
    - Differentiate new vs returning users.
    """
    try:
        user = update.effective_user
        if not user:
            logger.error("No user info available in update")
            await update.message.reply_text("Oops! Something went wrong. Try again later.")
            return

        # Prevent duplicate starts
        if context.user_data.get("last_start") == update.message.message_id:
            logger.info(f"Duplicate /start from {user.id}")
            return
        context.user_data["last_start"] = update.message.message_id

        telegram_id = str(user.id)
        session = get_session()  # Get session manually
        try:
            db_user = get_user(telegram_id, session)
            if not db_user:
                db_user = add_user(telegram_id, session)
                welcome_msg = (
                    f"Welcome, {user.first_name}! 🚀\n"
                    "You're new here! I'll set up your wallets soon.\n"
                    "What would you like to do?"
                )
            else:
                welcome_msg = (
                    f"Welcome back, {user.first_name}! 👋\n"
                    "Your trading bot is ready.\n"
                    "What would you like to do?"
                )
        finally:
            session.close()  # Ensure session is closed

        await update.message.reply_text(welcome_msg, reply_markup=MAIN_MENU)
        logger.info(f"Processed /start for user {telegram_id}")

    except Exception as e:
        logger.error(f"Error in start handler: {str(e)}")
        await update.message.reply_text("An error occurred. Please try again.")
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle inline button clicks (stub for now).

    Edge Cases:
    - Invalid callback data.
    """
    query = update.callback_query
    await query.answer()  # Acknowledge the callback

    if query.data in ["buy", "sell", "wallet", "help"]:
        await query.edit_message_text(f"You clicked {query.data}! Feature coming soon.")
    else:
        logger.warning(f"Unknown callback data: {query.data}")
        await query.edit_message_text("Invalid option. Use the menu below.", reply_markup=MAIN_MENU)

def main() -> None:
    """Initialize and run the Telegram bot."""
    try:
        app = Application.builder().token(TELEGRAM_TOKEN).build()

        # Register handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button))

        logger.info("Bot starting...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"Failed to start bot: {str(e)}")

if __name__ == "__main__":
    main()
