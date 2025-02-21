import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters
from services.token_info import get_token_info, format_token_info, detect_chain

logger = logging.getLogger(__name__)

async def token_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle plain text input of a token address or name, display token details.

    Args:
        update: Telegram update object.
        context: Telegram context object.

    Edge Cases:
    - Invalid address or unrecognized token name.
    - API fetch failures.
    """
    user_input = update.message.text.strip()
    user_id = str(update.effective_user.id)

    try:
        try:
            chain = detect_chain(user_input)
            is_address = True
        except ValueError:
            is_address = False

        if is_address:
            token_info = await get_token_info(user_input)  # Already async and awaited
            if not token_info:
                await update.message.reply_text("Couldn’t fetch token info. Check the address and try again.")
                return
        else:
            logger.info(f"Assuming {user_input} as token symbol (stubbed)")
            token_info = {
                "name": f"{user_input} Token",
                "symbol": user_input.upper(),
                "address": "StubAddress123",
                "price_usd": 0.01,
                "price_change_24h": 5.0,
                "market_cap": 10000,
                "volume_24h": 5000,
                "liquidity": 2000,
                "price_change_1h": 1.2,
                "buys_1h": 3,
                "sells_1h": 2,
                "ath": 15000,
                "ath_change": -33.3,
                "age_days": 7
            }

        # Format and display token info (await the async function)
        formatted_info = await format_token_info(token_info)  # Fix: Added await
        keyboard = [
            [InlineKeyboardButton("Buy", callback_data="buy_from_details"),
             InlineKeyboardButton("Sell", callback_data="sell_from_details")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(formatted_info, reply_markup=reply_markup, parse_mode="Markdown")
        logger.info(f"Displayed token details for {user_input} to user {user_id}")

    except Exception as e:
        logger.error(f"Error in token_details for {user_id}: {str(e)}")
        await update.message.reply_text("An error occurred. Please try a valid token address or name.")

# Handler for plain text input
token_details_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, token_details)