import logging
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

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
    await update.message.reply_text(help_message, parse_mode="Markdown")
    logger.info(f"Displayed help message to user {user_id}")

# Export handler
handler = CommandHandler("help", help_handler)