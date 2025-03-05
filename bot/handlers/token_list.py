import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

logger = logging.getLogger(__name__)

async def token_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display a placeholder for a token list in AI Mode."""
    user_id = str(update.effective_user.id)
    query = update.callback_query
    await query.answer()

    placeholder_message = (
        "📋 *Token List (AI Mode Preview)*\n\n"
        "Here’s a sample of tokens you might trade:\n"
        "- *TON*: $2.60 (+3.2%)\n"
        "- *USDT (TON)*: $1.00 (Stable)\n"
        "- *SOL*: $144.50 (+1.8%)\n"
        "- *USDC (SOL)*: $1.00 (Stable)\n"
        "- *SHIB (SOL)*: $0.000013 (+5.1%)\n\n"
        "This is a preview! Full token list coming soon."
    )
    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(placeholder_message, reply_markup=reply_markup, parse_mode="Markdown")
    logger.info(f"Displayed AI Mode token list to user {user_id}")

# Export handler
token_list_handler = CallbackQueryHandler(token_list_handler, pattern="^token_list$")