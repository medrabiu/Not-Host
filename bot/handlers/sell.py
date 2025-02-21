import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from services.token_info import get_token_info, format_token_info


from blockchain.solana.transactions import execute_solana_trade
from blockchain.ton.transactions import execute_ton_trade
from services.wallet_management import get_wallet
from services.token_info import detect_chain

logger = logging.getLogger(__name__)

# Conversation states
ADDRESS = 0

async def sell_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Sell' button, prompt for token address."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Please send the token address you want to sell.")
    return ADDRESS

async def sell_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Confirm Sell' button."""
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    token_info = context.user_data.get("sell_token")

    try:
        if not token_info:
            await query.edit_message_text("No token selected. Start over with /start.")
            return ConversationHandler.END

        chain = detect_chain(token_info["address"])
        wallet = get_wallet(user_id, chain)
        if not wallet:
            await query.edit_message_text("Wallet not found. Set up your wallet first.")
            return ConversationHandler.END

        if chain == "solana":
            tx_id = await execute_solana_trade(wallet.public_key, token_info["address"], 0.001)  # Stub amount
        else:  # ton
            tx_id = await execute_ton_trade(wallet.public_key, token_info["address"], 0.001)

        if tx_id:
            await query.edit_message_text(f"Sell successful! Tx ID: `{tx_id}`", parse_mode="Markdown")
        else:
            await query.edit_message_text("Sell failed. Try again later.")
        logger.info(f"Sell confirmed for {user_id} on {chain}")
    except Exception as e:
        logger.error(f"Error in sell_confirm for {user_id}: {str(e)}")
        await query.edit_message_text("An error occurred during the trade.")
    return ConversationHandler.END

async def sell_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process token address, display token info for sell."""
    token_address = update.message.text.strip()
    user_id = str(update.effective_user.id)

    try:
        token_info = get_token_info(token_address)
        if not token_info:
            await update.message.reply_text("Couldn’t fetch token info. Check the address and try again.")
            return ConversationHandler.END

        formatted_info = format_token_info(token_info).replace("Buy", "Sell")  # Adjust for sell context
        keyboard = [[InlineKeyboardButton("Confirm Sell", callback_data="confirm_sell"),
                     InlineKeyboardButton("Cancel", callback_data="cancel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(formatted_info, reply_markup=reply_markup, parse_mode="Markdown")
        context.user_data["sell_token"] = token_info  # Store for confirmation
        logger.info(f"Displayed sell info for {token_address} to user {user_id}")
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in sell_address for {user_id}: {str(e)}")
        await update.message.reply_text("An error occurred. Try again later.")
        return ConversationHandler.END

async def sell_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancellation of the sell process."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Sell cancelled. Use /start to return to the menu.")
    return ConversationHandler.END

# Define the conversation handler
sell_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(sell_start, pattern="^sell$")],
    states={
        ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_address)]
    },
    fallbacks=[
        CallbackQueryHandler(sell_cancel, pattern="^cancel$"),
        CallbackQueryHandler(sell_confirm, pattern="^confirm_sell$")  # Add confirmation
    ]
)