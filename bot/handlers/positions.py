import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

logger = logging.getLogger(__name__)

async def positions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display a placeholder for user’s trading positions in AI Mode."""
    user_id = str(update.effective_user.id)
    query = update.callback_query
    await query.answer()

    placeholder_message = (
        "📊 *Your Positions (AI Mode Preview)*\n\n"
        "Here’s what your positions might look like:\n"
        "- *TON/USDT*: 10 TON (Entry: $2.50, Current: $2.60, PnL: +$1.00)\n"
        "- *SOL/USDC*: 5 SOL (Entry: $140.00, Current: $144.50, PnL: +$22.50)\n\n"
        "This is a preview of what’s coming soon! Stay tuned for real position tracking."
    )
    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(placeholder_message, reply_markup=reply_markup, parse_mode="Markdown")
    logger.info(f"Displayed AI Mode positions to user {user_id}")

# Export handler
positions_handler = CallbackQueryHandler(positions_handler, pattern="^positions$")