import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

logger = logging.getLogger(__name__)

async def pnl_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display a placeholder for user’s PnL in AI Mode."""
    user_id = str(update.effective_user.id)
    query = update.callback_query
    await query.answer()

    placeholder_message = (
        "💰 *Your PnL (AI Mode Preview)*\n\n"
        "Here’s a sample of your trading performance:\n"
        "- *Total Trades*: 15\n"
        "- *TON Portfolio*: +$35.20 (+12.5%)\n"
        "- *SOL Portfolio*: +$67.80 (+8.9%)\n"
        "- *Overall PnL*: +$103.00\n\n"
        "This is a sneak peek! Full PnL tracking coming soon."
    )
    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(placeholder_message, reply_markup=reply_markup, parse_mode="Markdown")
    logger.info(f"Displayed AI Mode PnL to user {user_id}")

# Export handler
pnl_handler = CallbackQueryHandler(pnl_handler, pattern="^pnl$")