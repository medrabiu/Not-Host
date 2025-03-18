from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
import logging

logger = logging.getLogger(__name__)

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display an introductory message about the bot and support contact."""
    user_id = str(update.effective_user.id)
    help_message = (
        "👋 Welcome to *Not-Cotrader*! I'm your multi-chain trading bot, here to help you swap tokens on TON and Solana.\n\n"
        "🔹 *What I can do*:\n"
        "  - Swap TON tokens via STON.fi\n"
        "  - Swap Solana tokens via Jupiter DEX\n"
        "  - Provide token info and wallet balances\n\n"
        "For more help or to report issues, contact my creator: @aystek on Telegram.\n"
        "Use /start to begin trading!"
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(help_message, parse_mode="Markdown")
    else:
        await update.message.reply_text(help_message, parse_mode="Markdown")

    logger.info(f"Displayed help message to user {user_id}")

# Export handlers
handler = CommandHandler("help", help_handler)
callback_handler = CallbackQueryHandler(help_handler, pattern=r"^help$")  # Handle inline button clicks
