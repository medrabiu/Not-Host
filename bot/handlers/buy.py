import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters,CallbackQueryHandler
from services.token_info import get_token_info, format_token_info

logger = logging.getLogger(__name__)

# Conversation states
ADDRESS = 0

async def buy_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle 'Buy' button click, prompt for token address.

    Edge Cases:
    - User cancels or sends invalid input later.
    """
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Please send the token address you want to buy.")
    return ADDRESS

async def buy_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process token address, fetch and display token info.

    Edge Cases:
    - Invalid address format.
    - Token info fetch failure.
    """
    token_address = update.message.text.strip()
    user_id = str(update.effective_user.id)

    try:
        token_info = get_token_info(token_address)
        if not token_info:
            await update.message.reply_text("Couldn’t fetch token info. Please check the address and try again.")
            return ConversationHandler.END

        # Format and send token info
        formatted_info = format_token_info(token_info)
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(formatted_info, reply_markup=reply_markup, parse_mode="Markdown")
        logger.info(f"Displayed token info for {token_address} to user {user_id}")

        # Stub: Next step would be trade confirmation
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in buy_address for {user_id}: {str(e)}")
        await update.message.reply_text("An error occurred. Try again later.")
        return ConversationHandler.END

async def buy_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle cancellation of the buy process.
    """
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Buy cancelled. Use /start to return to the menu.")
    return ConversationHandler.END

# Define the conversation handler
buy_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(buy_start, pattern="^buy$")],
    states={
        ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_address)]
    },
    fallbacks=[CallbackQueryHandler(buy_cancel, pattern="^cancel$")]
)