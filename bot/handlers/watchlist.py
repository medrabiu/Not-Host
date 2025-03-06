import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from services.token_info import get_token_info, detect_chain
from database.db import get_async_session, add_watchlist_token, get_watchlist_tokens, delete_watchlist_token

logger = logging.getLogger(__name__)

# Conversation states
ADD_TOKEN = 0

async def display_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display the user's watchlist or prompt to add tokens if empty.

    Args:
        update (Update): The Telegram update object (may contain callback_query or message).
        context (ContextTypes.DEFAULT_TYPE): The Telegram context object.

    Returns:
        int: The conversation state (ConversationHandler.END).

    Raises:
        Exception: If message sending/editing fails due to Telegram API issues (except 'Message is not modified').
    """
    user_id = str(update.effective_user.id)
    query = update.callback_query

    async with await get_async_session() as session:
        watchlist = await get_watchlist_tokens(user_id, session)

    # Add timestamp to ensure uniqueness
    timestamp = datetime.now().strftime("%H:%M:%S")
    if not watchlist:
        message = (
            f"📋 *Your Watchlist is Empty* (Refreshed at {timestamp})\n\n"
            "Add tokens to track their prices and market info!"
        )
    else:
        message = f"📋 *Your Watchlist* (Refreshed at {timestamp})\n\n"
        for token in watchlist:
            result = await get_token_info(token["address"])
            if result:
                token_info, _ = result
                message += (
                    f"**{token_info['symbol']} - {token_info['name']}**\n"
                    f"Price: ${token_info['price_usd']:.6f} | Market Cap: ${token_info.get('market_cap', 0):,.2f}\n"
                    f"CA: `{token['address']}`\n"
                    f"[Quick Buy](tg://btn/quick_buy_{token['address']}) | "
                    f"[View Chart](https://dexscreener.com/{token['chain']}/{token['address']}) | "
                    f"[Delete](tg://btn/delete_{token['address']})\n\n"
                )
            else:
                message += (
                    f"**{token['symbol']} - {token['name']}**\n"
                    f"Price: N/A | Market Cap: N/A\n"
                    f"CA: `{token['address']}`\n"
                    f"[Quick Buy](tg://btn/quick_buy_{token['address']}) | "
                    f"[View Chart](https://dexscreener.com/{token['chain']}/{token['address']}) | "
                    f"[Delete](tg://btn/delete_{token['address']})\n\n"
                )

    keyboard = [
        [InlineKeyboardButton("Add Token", callback_data="add_token")],
        [InlineKeyboardButton("Refresh", callback_data="refresh_watchlist"),
         InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    try:
        if query:  # Called from a callback query (e.g., button press)
            await query.answer()
            await query.edit_message_text(
                message,
                reply_markup=markup,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        else:  # Called from a message (e.g., after adding a token)
            await update.message.reply_text(
                message,
                reply_markup=markup,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        logger.info(f"Displayed watchlist to user {user_id}")
    except Exception as e:
        if "Message is not modified" in str(e):
            logger.debug(f"Watchlist unchanged for user {user_id}, but timestamp forced update")
        else:
            logger.error(f"Failed to display watchlist for user {user_id}: {str(e)}", exc_info=True)
            if query:
                await query.edit_message_text("An error occurred while loading the watchlist. Please try again.")
            else:
                await update.message.reply_text("An error occurred while loading the watchlist. Please try again.")
    
    return ConversationHandler.END

async def watchlist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle watchlist interactions such as adding, refreshing, or deleting tokens.

    Args:
        update (Update): The Telegram update object containing the callback query.
        context (ContextTypes.DEFAULT_TYPE): The Telegram context object.

    Returns:
        int: The conversation state (ADD_TOKEN or ConversationHandler.END).

    Raises:
        Exception: If message editing fails due to Telegram API issues.
    """
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)

    if query.data == "add_token":
        try:
            await query.edit_message_text(
                "Please send the contract address (CA) of the token to add to your watchlist:",
                parse_mode="Markdown"
            )
            logger.info(f"Prompted user {user_id} to add a token")
            return ADD_TOKEN
        except Exception as e:
            logger.error(f"Failed to prompt add token for user {user_id}: {str(e)}", exc_info=True)
            await query.edit_message_text("An error occurred. Please try again.")
            return ConversationHandler.END

    elif query.data == "refresh_watchlist":
        await display_watchlist(update, context)
        logger.info(f"Refreshed watchlist for user {user_id}")
        return ConversationHandler.END

    elif query.data.startswith("delete_"):
        token_address = query.data.split("_")[1]
        async with await get_async_session() as session:
            await delete_watchlist_token(user_id, token_address, session)
        await display_watchlist(update, context)
        logger.info(f"User {user_id} deleted token {token_address} from watchlist")
        return ConversationHandler.END

    elif query.data.startswith("quick_buy_"):
        token_address = query.data.split("_")[2]
        update.message = Update(
            update.update_id,
            message=type("Message", (), {"text": token_address, "chat": query.message.chat, "message_id": query.message.message_id})
        )
        from bot.handlers.token_details import token_details_handler
        await token_details_handler(update, context)
        logger.info(f"User {user_id} triggered quick buy for {token_address}")
        return ConversationHandler.END

    return ConversationHandler.END

async def add_token_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Add a token to the watchlist and save it to the database.

    Args:
        update (Update): The Telegram update object containing the user's message.
        context (ContextTypes.DEFAULT_TYPE): The Telegram context object.

    Returns:
        int: The conversation state (ADD_TOKEN to retry or ConversationHandler.END to finish).

    Raises:
        Exception: If database operations or message sending fail.
    """
    user_id = str(update.effective_user.id)
    token_address = update.message.text.strip()

    try:
        chain = detect_chain(token_address)
    except ValueError:
        await update.message.reply_text(
            "Invalid contract address. Please enter a valid TON or Solana CA.",
            parse_mode="Markdown"
        )
        return ADD_TOKEN

    result = await get_token_info(token_address)
    if not result:
        await update.message.reply_text(
            "Couldn’t fetch token info. Check the address and try again.",
            parse_mode="Markdown"
        )
        return ADD_TOKEN

    token_info, _ = result
    token_data = {
        "address": token_address,
        "symbol": token_info["symbol"],
        "name": token_info["name"],
        "chain": chain
    }

    async with await get_async_session() as session:
        await add_watchlist_token(user_id, token_data, session)

    await update.message.reply_text(
        f"Added {token_info['symbol']} to your watchlist!",
        parse_mode="Markdown"
    )
    await display_watchlist(update, context)
    logger.info(f"User {user_id} added token {token_address} to watchlist")
    return ConversationHandler.END

watchlist_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(display_watchlist, pattern="^watchlist$"),
        CallbackQueryHandler(watchlist_callback, pattern="^(add_token|refresh_watchlist|delete_|quick_buy_)")
    ],
    states={
        ADD_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_token_handler)]
    },
    fallbacks=[CallbackQueryHandler(display_watchlist, pattern="^main_menu$")]
)

watchlist_handler = watchlist_conv_handler