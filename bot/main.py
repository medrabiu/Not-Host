import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest
from database.db import get_async_session, get_user, add_user
from bot.handlers.buy import buy_handler
from bot.handlers.wallet import wallet_handler, wallet_callbacks
from bot.handlers.token_details import token_details_handler
from bot.handlers.sell import sell_handler
from bot.handlers.start import start_handler, start_callback_handler
from bot.handlers.settings import settings_handler  
from bot.handlers.help import handler as help_command_handler, callback_handler as help_callback_handler
from bot.handlers.settings import settings_command_handler, settings_callback_handler, settings_input_handler
from bot.handlers.positions import positions_handler
from bot.handlers.pnl import pnl_handler
from bot.handlers.token_list import token_list_handler
from bot.handlers.watchlist import watchlist_handler
from dotenv import load_dotenv

load_dotenv()
# Configure logging to save to a file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),  # Save logs to bot.log
        logging.StreamHandler()          # Optional: Keep console output
    ]
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    logger.critical("TELEGRAM_TOKEN is missing from the environment!")
    sys.exit(1)


MAIN_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("🟩 Buy", callback_data="buy"),
     InlineKeyboardButton("🟥 Sell", callback_data="sell")],
    [InlineKeyboardButton("Positions", callback_data="positions"),
     InlineKeyboardButton("Token List", callback_data="token_list")],
    [InlineKeyboardButton("P&L", callback_data="pnl"),
     InlineKeyboardButton("Watchlist", callback_data="watchlist")], 
    [InlineKeyboardButton("Wallet", callback_data="wallet"),
     InlineKeyboardButton("Settings", callback_data="settings"),
     InlineKeyboardButton("Feedback", callback_data="feedback")],
    [InlineKeyboardButton("Help", callback_data="help")]
])

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the main menu display and basic button clicks.

    This function processes callback queries for the main menu, displaying the menu
    or redirecting to specific handlers based on the button clicked.

    Args:
        update (Update): The Telegram update object containing the callback query.
        context (ContextTypes.DEFAULT_TYPE): The Telegram context object.

    Returns:
        None

    Notes:
        - Logs user interactions and warns on unknown callback data.
        - Provides a fallback message for unhandled options.
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == "main_menu":
        await query.edit_message_text("Welcome to Not-Cotrader! Choose an option:", reply_markup=MAIN_MENU)
        logger.info(f"User {update.effective_user.id} returned to main menu")
    elif query.data == "settings":
        await settings_handler(update, context)  # Call the settings handler directly
    
    else:
        logger.warning(f"Unknown callback data: {query.data}")
        await query.edit_message_text("Invalid option. Use the menu below.", reply_markup=MAIN_MENU)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle uncaught exceptions and notify the user, suppressing 'Message is not modified' errors.

    This function logs errors and sends an error message to the user, while ignoring
    non-critical Telegram BadRequest errors related to unchanged messages.

    Args:
        update (Update): The Telegram update object (may be None).
        context (ContextTypes.DEFAULT_TYPE): The Telegram context object containing the error.

    Returns:
        None

    Notes:
        - Logs full exception details with stack traces for debugging.
        - Handles both callback queries and message updates appropriately.
    """
    if isinstance(context.error, BadRequest) and "Message is not modified" in str(context.error):
        logger.debug("Suppressed 'Message is not modified' error")
        return

    logger.error(f"Exception occurred: {context.error}", exc_info=True)
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("An error occurred. Please try again later.", parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text("An error occurred. Please try again later.", parse_mode="Markdown")
    else:
        logger.warning("Update object has no query or message to respond to.")

def main() -> None:
    """
    Initialize and run the Telegram bot.

    This function sets up the Telegram bot application, registers all handlers,
    and starts the polling loop with job queue support.

    Returns:
        None

    Raises:
        Exception: If bot initialization or polling fails (logged as critical).

    Notes:
        - Registers handlers in a specific order: specific handlers first, catch-all last.
        - Starts the job queue for scheduled tasks.
    """
    try:
        app = Application.builder().token(TELEGRAM_TOKEN).build()

        # Register handlers (specific handlers first, catch-all last)
        app.add_handler(start_handler)
        app.add_handler(start_callback_handler)
        app.add_handler(wallet_handler)
        for callback in wallet_callbacks:
            app.add_handler(callback)
        app.add_handler(buy_handler)
        app.add_handler(sell_handler)
        app.add_handler(watchlist_handler)
        app.add_handler(token_details_handler)
        app.add_handler(help_command_handler) 
        app.add_handler(help_callback_handler)  
        app.add_handler(settings_command_handler)
        app.add_handler(settings_callback_handler)
        app.add_handler(settings_input_handler)
        app.add_handler(positions_handler)
        app.add_handler(pnl_handler)
        app.add_handler(token_list_handler)
     
        app.add_handler(CallbackQueryHandler(main_menu_handler, pattern=r"^(main_menu|buy|sell|settings|wallet|positions|pnl|token_list|help)$"))

        # Error handler
        app.add_error_handler(error_handler)

        # Initialize the job queue
        app.job_queue.start() 

        logger.info("Bot starting with job queue enabled...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"Failed to start bot: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()