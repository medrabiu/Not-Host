# bot/handlers/feedback.py
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler

logger = logging.getLogger(__name__)
from dotenv import load_dotenv
load_dotenv()

# Define states for the conversation
FEEDBACK_TEXT = 0


FEEDBACK_CHANNEL_ID =os.getenv("FEEDBACK_CHANNEL_ID")
if not FEEDBACK_CHANNEL_ID:
    logger.critical("FEEDBACK_CHANNEL_ID is missing from the environment!")
    raise ValueError("FEEDBACK_CHANNEL_ID must be set in .env")

async def feedback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initiate the feedback process."""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_feedback")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "We appreciate your feedback! Please share your thoughts, suggestions, or any issues you've encountered:",
        reply_markup=reply_markup
    )
    logger.info(f"User {update.effective_user.id} started feedback process")
    return FEEDBACK_TEXT

async def receive_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the feedback text and send it to the channel."""
    user = update.effective_user
    feedback_text = update.message.text
    
    # Format the feedback message
    feedback_message = (
        f"New Feedback Received\n"
        f"From: {user.full_name} (ID: {user.id})\n"
        f"Username: @{user.username if user.username else 'N/A'}\n" # pulic for now can be anonymous best practice
        f"Message: {feedback_text}"
    )
    
    # Send feedback to the channel
    try:
        await context.bot.send_message(
            chat_id=FEEDBACK_CHANNEL_ID,
            text=feedback_message,
            parse_mode="Markdown"
        )
        logger.info(f"Feedback from user {user.id} successfully sent to channel {FEEDBACK_CHANNEL_ID}")
        
        # Confirm with the user
        await update.message.reply_text(
            "Thank you for your feedback! It has been successfully submitted. stay in touch",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Main Menu", callback_data="main_menu")]])
        )
    except Exception as e:
        logger.error(f"Failed to send feedback to channel: {str(e)}")
        await update.message.reply_text(
            "Sorry, there was an error submitting your feedback. Please try again later.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Main Menu", callback_data="main_menu")]])
        )
    
    return ConversationHandler.END

async def cancel_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the feedback process."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "Feedback cancelled.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Main Menu", callback_data="main_menu")]])
    )
    logger.info(f"User {update.effective_user.id} cancelled feedback")
    return ConversationHandler.END

# Define the conversation handler
feedback_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(feedback_handler, pattern="^feedback$")],
    states={
        FEEDBACK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_feedback)],
    },
    fallbacks=[CallbackQueryHandler(cancel_feedback, pattern="^cancel_feedback$")]
)