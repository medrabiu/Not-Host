import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from database.db import get_async_session, get_user, add_user
from bot.handlers.buy import buy_handler
from bot.handlers.wallet import wallet_handler
from bot.handlers.token_details import token_details_handler
from bot.handlers.sell import sell_handler
from bot.handlers.start import start_handler, start_callback_handler  # Updated imports

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = "7754246943:AAFT82vJoG8g0zVb10HeSRfrhP6TSh0AyNM"

MAIN_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("Buy", callback_data="buy"),
     InlineKeyboardButton("Sell", callback_data="sell")],
    [InlineKeyboardButton("Wallet", callback_data="wallet"),
     InlineKeyboardButton("Help", callback_data="help")]
])

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle inline button clicks (stub for now).

    Edge Cases:
    - Invalid callback data.
    """
    query = update.callback_query
    await query.answer()

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
        app.add_handler(start_handler)
        app.add_handler(start_callback_handler)
        app.add_handler(CallbackQueryHandler(wallet_handler, pattern="^wallet$"))
        app.add_handler(buy_handler)
        app.add_handler(sell_handler)
        app.add_handler(token_details_handler)
        app.add_handler(CallbackQueryHandler(button))

        logger.info("Bot starting...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"Failed to start bot: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()