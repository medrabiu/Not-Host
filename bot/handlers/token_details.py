import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters
from services.token_info import get_token_info, format_token_info, detect_chain
from database.db import get_async_session  # Updated import
from services.wallet_management import get_wallet

logger = logging.getLogger(__name__)

async def token_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text input of a token address, display details with image."""
    user_input = update.message.text.strip()
    user_id = str(update.effective_user.id)

    try:
        chain = detect_chain(user_input)
        result = await get_token_info(user_input)
        if not result:
            await update.message.reply_text("Couldn’t fetch token info. Check the address and try again.")
            return
        token_info, chain_price_usd = result

        async with (await get_async_session()) as session:  # Async session context
            wallet = await get_wallet(user_id, chain, session)
            wallet_balance = 0.05 if chain == "solana" else 0.1  # Stubbed; replace with actual balance

        formatted_info = await format_token_info(token_info, chain, wallet_balance, chain_price_usd)
        amounts = [0.01, 0.02, 0.03, 0.04, 0.05] if chain == "solana" else [0.02, 0.04, 0.06, 0.08, 0.1]
        unit = "SOL" if chain == "solana" else "TON"
        keyboard = [
            [InlineKeyboardButton(f"{amt} {unit}", callback_data=f"buy_{amt}") for amt in amounts],
            [InlineKeyboardButton(f"Buy {amounts[0]} {unit}", callback_data=f"buy_{amounts[0]}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(formatted_info, reply_markup=reply_markup, parse_mode="Markdown")
        context.user_data["token_info"] = token_info
        context.user_data["chain"] = chain
        logger.info(f"Displayed token details for {user_input} to user {user_id}")

    except ValueError:
        await update.message.reply_text("Invalid token address.")
    except Exception as e:
        logger.error(f"Error in token_details for {user_id}: {str(e)}")
        await update.message.reply_text("An error occurred. Try again later.")

token_details_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, token_details)