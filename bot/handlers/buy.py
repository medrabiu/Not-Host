import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from services.token_info import get_token_info, format_token_info
from blockchain.solana.transactions import execute_solana_trade
from blockchain.ton.transactions import execute_ton_trade
from services.wallet_management import get_wallet
from services.token_info import detect_chain

logger = logging.getLogger(__name__)

# Conversation states
ADDRESS, CONFIRM = range(2)

async def buy_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Buy' button click, prompt for token address."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Please send the token address you want to buy.")
    return ADDRESS

async def buy_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process token address, fetch and display token info, move to confirmation."""
    token_address = update.message.text.strip()
    user_id = str(update.effective_user.id)

    try:
        token_info = get_token_info(token_address)
        if not token_info:
            await update.message.reply_text("Couldn’t fetch token info. Check the address and try again.")
            return ConversationHandler.END

        formatted_info = format_token_info(token_info)
        keyboard = [[InlineKeyboardButton("Confirm Buy", callback_data="confirm_buy"),
                     InlineKeyboardButton("Cancel", callback_data="cancel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(formatted_info, reply_markup=reply_markup, parse_mode="Markdown")
        context.user_data["buy_token"] = token_info
        logger.info(f"Displayed buy info for {token_address} to user {user_id}")
        return CONFIRM  # Move to confirmation state instead of ending
    except Exception as e:
        logger.error(f"Error in buy_address for {user_id}: {str(e)}")
        await update.message.reply_text("An error occurred. Try again later.")
        return ConversationHandler.END

async def buy_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Confirm Buy' button."""
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    token_info = context.user_data.get("buy_token")

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
            await query.edit_message_text(f"Buy successful! Tx ID: `{tx_id}`", parse_mode="Markdown")
        else:
            await query.edit_message_text("Buy failed. Try again later.")
        logger.info(f"Buy confirmed for {user_id} on {chain}")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in buy_confirm for {user_id}: {str(e)}")
        await query.edit_message_text("An error occurred during the trade.")
        return ConversationHandler.END

async def buy_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancellation of the buy process."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Buy cancelled. Use /start to return to the menu.")
    return ConversationHandler.END

# Define the conversation handler
buy_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(buy_start, pattern="^buy$")],
    states={
        ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_address)],
        CONFIRM: [CallbackQueryHandler(buy_confirm, pattern="^confirm_buy$"),
                  CallbackQueryHandler(buy_cancel, pattern="^cancel$")]
    },
    fallbacks=[CallbackQueryHandler(buy_cancel, pattern="^cancel$")]
)