import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes  # No need for MessageHandler here
from services.token_info import get_token_info, format_token_info, detect_chain
from database.db import get_async_session
from services.wallet_management import get_wallet
from services.utils import get_wallet_balance_and_usd

logger = logging.getLogger(__name__)

async def token_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display token details and trade options when a user sends a token address."""
    user_id = str(update.effective_user.id)
    user_input = update.message.text.strip()

    try:
        chain = detect_chain(user_input)  # This raises ValueError if not a valid address
        unit = "SOL" if chain == "solana" else "TON"
        result = await get_token_info(user_input)
        if not result:
            await update.message.reply_text("Couldn’t fetch token info. Check the address and try again.")
            return
        token_info, chain_price_usd = result

        async with (await get_async_session()) as session:
            wallet = await get_wallet(user_id, chain, session)
            if not wallet:
                await update.message.reply_text(f"No {chain.capitalize()} wallet found. Create one first!", parse_mode="Markdown")
                return
            wallet_balance, usd_value = await get_wallet_balance_and_usd(wallet.public_key, chain)

        formatted_info = await format_token_info(token_info, chain, wallet_balance, chain_price_usd)
        default_amount = 0.5  # Default buy amount

        # Store trade setup in context
        context.user_data["token_address"] = user_input
        context.user_data["token_info"] = token_info
        context.user_data["chain"] = chain
        context.user_data["slippage"] = 5
        context.user_data["buy_amount"] = default_amount

        keyboard = [
            [InlineKeyboardButton(f"Slippage: {context.user_data['slippage']}%", callback_data="set_slippage"),
             InlineKeyboardButton(f"Amount: {default_amount} {unit}", callback_data="set_amount")],
            [InlineKeyboardButton("Execute Trade", callback_data="execute_trade"),
             InlineKeyboardButton("Refresh", callback_data="refresh_token")],
            [InlineKeyboardButton("Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(formatted_info, reply_markup=reply_markup, parse_mode="Markdown")
        logger.info(f"Displayed token details for {user_input} to user {user_id}")

    except ValueError:
        raise  # Let the dispatcher handle this
    except Exception as e:
        logger.error(f"Error in token_details for {user_id}: {str(e)}")
        await update.message.reply_text("An error occurred. Try again later.")
