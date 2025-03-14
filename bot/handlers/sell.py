import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from database.db import get_async_session
from services.wallet_management import get_wallet
from services.utils import get_wallet_balance_and_usd, get_token_balance
from services.token_info import get_token_info, format_token_info, detect_chain
from blockchain.solana.trade import execute_solana_swap  # Placeholder; implement this if not already done
from blockchain.ton.sell import execute_jetton_to_ton_swap
from handlers.constants import MAIN_MENU  # Import MAIN_MENU from constants.py

logger = logging.getLogger(__name__)

# Conversation states
TOKEN_ADDRESS, SET_AMOUNT, SET_SLIPPAGE, CONFIRM = range(4)

async def sell_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)

    if query.data == "sell_execute_trade":
        return await confirm_sell(update, context)

    if query.data.startswith("set_amount"):
        await query.edit_message_text("Enter the amount of tokens to sell (e.g., 1.0):", parse_mode="Markdown")
        return SET_AMOUNT

    if query.data.startswith("set_slippage"):
        await query.edit_message_text("Enter slippage percentage (e.g., 5):", parse_mode="Markdown")
        return SET_SLIPPAGE

    if query.data == "refresh_token":
        return await refresh_token(update, context)

    msg = "Please send the token address you want to sell:"
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
        # For sell, we need token balance, not native currency balance
        # Assuming get_token_balance exists or is added to services.utils
        token_balance = await get_token_balance(wallet.public_key, token_address, chain)
        wallet_balance, _ = await get_wallet_balance_and_usd(wallet.public_key, chain)  # Still fetch TON/SOL for gas

    result = await get_token_info(token_address)
    if not result:
        await update.message.reply_text("Couldn’t fetch token info. Check the address and try again.")
        return TOKEN_ADDRESS
    token_info, chain_price_usd = result

    context.user_data["token_address"] = token_address
    context.user_data["token_info"] = token_info
    context.user_data["chain"] = chain
    context.user_data["sell_amount"] = 1.0  # Default sell amount
    context.user_data["slippage"] = 5.0  # Default slippage

    formatted_info = await format_token_info(token_info, chain, wallet_balance, chain_price_usd, context)
    keyboard = [
        [InlineKeyboardButton(f"Slippage: {context.user_data['slippage']}%", callback_data="set_slippage"),
         InlineKeyboardButton(f"Amount: {context.user_data['sell_amount']} {token_info['symbol']}", callback_data="set_amount")],
        [InlineKeyboardButton("Execute Trade", callback_data="sell_execute_trade"),
         InlineKeyboardButton("Refresh", callback_data="refresh_token")],
        [InlineKeyboardButton("Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(formatted_info, reply_markup=reply_markup, parse_mode="Markdown")
    logger.info(f"Displayed token details for sell {token_address} to user {user_id}")
    return CONFIRM

async def set_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    try:
        amount = float(update.message.text.strip())
        if amount <= 0:
            raise ValueError
        context.user_data["sell_amount"] = amount
    except ValueError:
        await update.message.reply_text("Invalid amount. Enter a positive number (e.g., 1.0).", parse_mode="Markdown")
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
        token_balance = await get_token_balance(wallet.public_key, token_address, chain)
        wallet_balance, usd_value = await get_wallet_balance_and_usd(wallet.public_key, chain)

    result = await get_token_info(token_address)
    if not result:
        await (update.message.reply_text if from_message else update.callback_query.edit_message_text)(
            "Couldn’t refresh token info. Try again later.", parse_mode="Markdown"
        )
        return CONFIRM
    token_info, chain_price_usd = result
    context.user_data["token_info"] = token_info

    formatted_info = await format_token_info(token_info, chain, wallet_balance, chain_price_usd, context, is_sell=True)
    sell_amount = context.user_data.get("sell_amount", 1.0)
    slippage = context.user_data.get("slippage", 5.0)

    keyboard = [
        [InlineKeyboardButton(f"Slippage: {slippage}%", callback_data="set_slippage"),
         InlineKeyboardButton(f"Amount: {sell_amount} {token_info['symbol']}", callback_data="set_amount")],
        [InlineKeyboardButton("Execute Trade", callback_data="sell_execute_trade"),
         InlineKeyboardButton("Refresh", callback_data="refresh_token")],
        [InlineKeyboardButton("Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if from_message:
        await update.message.reply_text(formatted_info, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(formatted_info, reply_markup=reply_markup, parse_mode="Markdown")
    logger.info(f"Refreshed token details for sell {token_address} for user {user_id}")
    return CONFIRM

async def confirm_sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)

    token_address = context.user_data["token_address"]
    chain = context.user_data["chain"]
    amount = context.user_data["sell_amount"]
    slippage = context.user_data["slippage"]
    unit = "SOL" if chain == "solana" else "TON"

    async with await get_async_session() as session:
        wallet = await get_wallet(user_id, chain, session)
        token_balance = await get_token_balance(wallet.public_key, token_address, chain)
        wallet_balance, _ = await get_wallet_balance_and_usd(wallet.public_key, chain)  # For gas check

    if token_balance < amount:
        await query.edit_message_text(
            f"Insufficient token balance. You have {token_balance:.6f} {context.user_data['token_info']['symbol']}, "
            f"need {amount:.6f}.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    # Check TON/SOL balance for gas (rough estimate)
    gas_buffer = 0.01 if chain == "solana" else 0.2  # SOL or TON
    if wallet_balance < gas_buffer:
        await query.edit_message_text(
            f"Insufficient {unit} for gas. You have {wallet_balance:.6f} {unit}, need at least {gas_buffer:.6f}.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    token_info = context.user_data["token_info"]
    formatted_info = await format_token_info(token_info, chain, wallet_balance, 0, context, is_sell=True)

    try:
        if chain == "solana":
            swap_result = await execute_solana_sell_swap(wallet, token_address, amount, slippage)
            output_amount = swap_result["output_amount"] / 1_000_000_000  # Assuming SOL output in lamports
            tx_id = swap_result["tx_id"]
            msg = (
                f"{formatted_info}\n\n"
                f"Sell Order Executed:\n"
                f"Sold: {amount:.6f} {token_info['symbol']}\n"
                f"Received: {output_amount:.6f} SOL\n"
                f"Tx: [Solscan](https://solscan.io/tx/{tx_id})"
            )
        elif chain == "ton":
            # Convert slippage percentage to basis points (5% = 500 bps)
            swap_result = await execute_jetton_to_ton_swap(wallet, token_address, amount, int(slippage * 100))
            output_amount = swap_result["output_amount"] / 1_000_000_000  # TON in nanoTON
            tx_id = swap_result["tx_id"]
            msg = (
                f"{formatted_info}\n\n"
                f"Sell Order Executed:\n"
                f"Sold: {amount:.6f} {token_info['symbol']}\n"
                f"Received: {output_amount:.6f} TON\n"
                f"Tx: [TONScan](https://tonscan.org/tx/{tx_id})"
            )
        else:
            raise ValueError(f"Unsupported chain: {chain}")

        await query.edit_message_text(msg, parse_mode="Markdown")
        logger.info(f"User {user_id} executed sell {amount} {token_info['symbol']} for {unit} on {chain}")

    except Exception as e:
        await query.edit_message_text(f"Failed to execute {chain.capitalize()} sell: {str(e)}", parse_mode="Markdown")
        logger.error(f"Sell failed for user {user_id}: {str(e)}", exc_info=True)

    return ConversationHandler.END

async def cancel_sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Sell cancelled. Choose an option:", reply_markup=MAIN_MENU, parse_mode="Markdown")
    logger.info(f"User {update.effective_user.id} cancelled sell")
    return ConversationHandler.END

sell_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(sell_handler, pattern="^sell$"),
        CallbackQueryHandler(sell_handler, pattern="^sell_execute_trade$"),
        CallbackQueryHandler(sell_handler, pattern="^set_amount$"),
        CallbackQueryHandler(sell_handler, pattern="^set_slippage$"),
        CallbackQueryHandler(sell_handler, pattern="^refresh_token$"),
    ],
    states={
        TOKEN_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, token_address_handler)],
        SET_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_amount_handler)],
        SET_SLIPPAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_slippage_handler)],
        CONFIRM: [
            CallbackQueryHandler(sell_handler, pattern="^(sell_execute_trade|set_amount|set_slippage|refresh_token)$"),
            CallbackQueryHandler(cancel_sell, pattern="^main_menu$"),
        ]
    },
    fallbacks=[CallbackQueryHandler(cancel_sell, pattern="^main_menu$")]
)
