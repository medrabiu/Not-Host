import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from database.db import get_async_session
from services.wallet_management import get_wallet
from services.utils import get_wallet_balance_and_usd
from services.token_info import get_token_info, format_token_info, detect_chain
from blockchain.solana.trade import execute_solana_swap
from blockchain.ton.trade import execute_ton_swap

logger = logging.getLogger(__name__)

# Conversation states (reintroduced SET_SLIPPAGE)
TOKEN_ADDRESS, SET_AMOUNT, SET_SLIPPAGE, CONFIRM = range(4)

async def buy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)

    if query.data == "execute_trade":
        return await confirm_buy(update, context)

    if query.data.startswith("set_amount"):
        await query.edit_message_text("Enter the amount to buy (e.g., 0.5 for SOL, 1.5 for TON):", parse_mode="Markdown")
        return SET_AMOUNT

    if query.data.startswith("set_slippage"):
        await query.edit_message_text("Enter slippage percentage (e.g., 5):", parse_mode="Markdown")
        return SET_SLIPPAGE

    if query.data == "refresh_token":
        return await refresh_token(update, context)

    msg = "Please send the token address you want to buy:"
    await query.edit_message_text(msg, parse_mode="Markdown")
    return TOKEN_ADDRESS

async def token_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    token_address = update.message.text.strip()
    chain = detect_chain(token_address)
    unit = "SOL" if chain == "solana" else "TON"

    async with await get_async_session() as session:
        wallet = await get_wallet(user_id, chain, session)
        if not wallet:
            await update.message.reply_text(f"No {chain.capitalize()} wallet found. Create one first!", parse_mode="Markdown")
            return ConversationHandler.END
        wallet_balance, usd_value = await get_wallet_balance_and_usd(wallet.public_key, chain)

    result = await get_token_info(token_address)
    if not result:
        await update.message.reply_text("Couldn’t fetch token info. Check the address and try again.")
        return TOKEN_ADDRESS
    token_info, chain_price_usd = result

    context.user_data["token_address"] = token_address
    context.user_data["token_info"] = token_info
    context.user_data["chain"] = chain
    context.user_data["buy_amount"] = 0.5 if chain == "solana" else 1.5
    context.user_data["slippage"] = 5.0  # Default manual slippage

    formatted_info = await format_token_info(token_info, chain, wallet_balance, chain_price_usd, context)
    keyboard = [
        [InlineKeyboardButton(f"Slippage: {context.user_data['slippage']}%", callback_data="set_slippage"),
         InlineKeyboardButton(f"Amount: {context.user_data['buy_amount']} {unit}", callback_data="set_amount")],
        [InlineKeyboardButton("Execute Trade", callback_data="execute_trade"),
         InlineKeyboardButton("Refresh", callback_data="refresh_token")],
        [InlineKeyboardButton("Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(formatted_info, reply_markup=reply_markup, parse_mode="Markdown")
    logger.info(f"Displayed token details for {token_address} to user {user_id}")
    return CONFIRM

async def set_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    try:
        amount = float(update.message.text.strip())
        if amount <= 0:
            raise ValueError
        context.user_data["buy_amount"] = amount
    except ValueError:
        await update.message.reply_text("Invalid amount. Enter a positive number (e.g., 0.5 for SOL, 1.5 for TON).", parse_mode="Markdown")
        return SET_AMOUNT
    return await refresh_token(update, context, from_message=True)

async def set_slippage_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    try:
        slippage = float(update.message.text.strip())
        if slippage < 0 or slippage > 100:
            raise ValueError
        context.user_data["slippage"] = slippage
    except ValueError:
        await update.message.reply_text("Invalid slippage. Enter a number between 0 and 100 (e.g., 5).", parse_mode="Markdown")
        return SET_SLIPPAGE
    return await refresh_token(update, context, from_message=True)

async def refresh_token(update: Update, context: ContextTypes.DEFAULT_TYPE, from_message: bool = False) -> int:
    user_id = str(update.effective_user.id)
    token_address = context.user_data.get("token_address")
    chain = context.user_data.get("chain")
    if not token_address or not chain:
        await (update.message.reply_text if from_message else update.callback_query.edit_message_text)(
            "No token selected. Please send a token address first.", parse_mode="Markdown"
        )
        return ConversationHandler.END

    async with await get_async_session() as session:
        wallet = await get_wallet(user_id, chain, session)
        wallet_balance, usd_value = await get_wallet_balance_and_usd(wallet.public_key, chain)

    result = await get_token_info(token_address)
    if not result:
        await (update.message.reply_text if from_message else update.callback_query.edit_message_text)(
            "Couldn’t refresh token info. Try again later.", parse_mode="Markdown"
        )
        return CONFIRM
    token_info, chain_price_usd = result
    context.user_data["token_info"] = token_info

    formatted_info = await format_token_info(token_info, chain, wallet_balance, chain_price_usd, context)
    unit = "SOL" if chain == "solana" else "TON"
    buy_amount = context.user_data.get("buy_amount", 0.5 if chain == "solana" else 1.5)
    slippage = context.user_data.get("slippage", 5.0)

    keyboard = [
        [InlineKeyboardButton(f"Slippage: {slippage}%", callback_data="set_slippage"),
         InlineKeyboardButton(f"Amount: {buy_amount} {unit}", callback_data="set_amount")],
        [InlineKeyboardButton("Execute Trade", callback_data="execute_trade"),
         InlineKeyboardButton("Refresh", callback_data="refresh_token")],
        [InlineKeyboardButton("Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if from_message:
        await update.message.reply_text(formatted_info, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(formatted_info, reply_markup=reply_markup, parse_mode="Markdown")
    logger.info(f"Refreshed token details for {token_address} for user {user_id}")
    return CONFIRM

async def confirm_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)

    token_address = context.user_data["token_address"]
    chain = context.user_data["chain"]
    amount = context.user_data["buy_amount"]
    slippage = context.user_data["slippage"]
    unit = "SOL" if chain == "solana" else "TON"

    async with await get_async_session() as session:
        wallet = await get_wallet(user_id, chain, session)
        balance, usd_value = await get_wallet_balance_and_usd(wallet.public_key, chain)

    if balance < amount + 0.01:
        await query.edit_message_text(
            f"Insufficient {unit} balance. You have {balance:.2f} {unit}, need {amount + 0.01:.2f} {unit}.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    token_info = context.user_data["token_info"]
    formatted_info = await format_token_info(token_info, chain, balance, 0, context)

    try:
        if chain == "solana":
            swap_result = await execute_solana_swap(wallet, token_address, amount, slippage)
            output_amount = swap_result["output_amount"] / 1_000_000_000
            tx_id = swap_result["tx_id"]
            msg = (
                f"{formatted_info}\n\n"
                f"Buy Order Executed:\n"
                f"Spent: {amount:.2f} SOL\n"
                f"Received: {output_amount:.6f} {token_info['symbol']}\n"
                f"Tx: [Solscan](https://solscan.io/tx/{tx_id})"
            )
        elif chain == "ton":
            swap_result = await execute_ton_swap(wallet, token_address, amount, slippage)
            output_amount = swap_result["output_amount"] / 1_000_000_000
            tx_id = swap_result["tx_id"]
            msg = (
                f"{formatted_info}\n\n"
                f"Buy Order Executed:\n"
                f"Spent: {amount:.2f} TON\n"
                f"Received: {output_amount:.6f} {token_info['symbol']}\n"
                f"Tx: [TONScan](https://tonscan.org/tx/{tx_id})"
            )
        else:
            raise ValueError(f"Unsupported chain: {chain}")

        await query.edit_message_text(msg, parse_mode="Markdown")
        logger.info(f"User {user_id} executed buy {amount} {unit} of {token_address} on {chain}")

    except Exception as e:
        await query.edit_message_text(f"Failed to execute {chain.capitalize()} trade: {str(e)}", parse_mode="Markdown")
        logger.error(f"Swap failed for user {user_id}: {str(e)}", exc_info=True)

    return ConversationHandler.END

async def cancel_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Buy cancelled.", parse_mode="Markdown")
    logger.info(f"User {update.effective_user.id} cancelled buy")
    return ConversationHandler.END

buy_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(buy_handler, pattern="^buy$"),
        CallbackQueryHandler(buy_handler, pattern="^execute_trade$"),
        CallbackQueryHandler(buy_handler, pattern="^set_amount$"),
        CallbackQueryHandler(buy_handler, pattern="^set_slippage$"),
        CallbackQueryHandler(buy_handler, pattern="^refresh_token$"),
    ],
    states={
        TOKEN_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, token_address_handler)],
        SET_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_amount_handler)],
        SET_SLIPPAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_slippage_handler)],
        CONFIRM: [
            CallbackQueryHandler(buy_handler, pattern="^(execute_trade|set_amount|set_slippage|refresh_token)$"),
            CallbackQueryHandler(cancel_buy, pattern="^main_menu$"),
        ]
    },
    fallbacks=[CallbackQueryHandler(cancel_buy, pattern="^main_menu$")]
)

buy_handler = buy_conv_handler