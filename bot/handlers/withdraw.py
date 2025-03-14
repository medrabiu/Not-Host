# bot/handlers/withdraw.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from database.db import get_async_session
from services.wallet_management import get_wallet
from services.utils import get_wallet_balance_and_usd
from services.crypto import CIPHER
from handlers.constants import MAIN_MENU
from blockchain.ton.withdraw import send_ton_transaction 
# from blockchain.solana.withdraw import send_solana_transaction

logger = logging.getLogger(__name__)

# Conversation states
WITHDRAW_AMOUNT, DESTINATION_ADDRESS, CONFIRM_WITHDRAW = range(3)

async def withdraw_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    chain = "solana" if "solana" in query.data else "ton"
    chain_unit = "SOL" if chain == "solana" else "TON"
    gas_reserve = 0.0001 if chain == "solana" else 0.002  # Gas reserve for SOL or TON

    async with await get_async_session() as session:
        wallet = await get_wallet(user_id, chain, session)
        if not wallet:
            await query.edit_message_text(f"No {chain.capitalize()} wallet found. Create one first!", parse_mode="Markdown")
            return ConversationHandler.END
        balance, _ = await get_wallet_balance_and_usd(wallet.public_key, chain)
        if balance <= gas_reserve:
            await query.edit_message_text(
                f"Insufficient {chain_unit} balance. You have {balance:.6f} {chain_unit}, need at least {gas_reserve:.6f} for gas.",
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        context.user_data["withdraw_amount"] = balance - gas_reserve
        context.user_data["chain"] = chain

    await query.edit_message_text(
        f"Please send the {chain_unit} destination address where you want to withdraw all your {chain_unit}:",
        parse_mode="Markdown"
    )
    return DESTINATION_ADDRESS

async def withdraw_x(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    chain = "solana" if "solana" in query.data else "ton"
    chain_unit = "SOL" if chain == "solana" else "TON"
    gas_reserve = 0.01 if chain == "solana" else 0.2

    async with await get_async_session() as session:
        wallet = await get_wallet(user_id, chain, session)
        if not wallet:
            await query.edit_message_text(f"No {chain.capitalize()} wallet found. Create one first!", parse_mode="Markdown")
            return ConversationHandler.END
        balance, _ = await get_wallet_balance_and_usd(wallet.public_key, chain)
        if balance <= gas_reserve:
            await query.edit_message_text(
                f"Insufficient {chain_unit} balance. You have {balance:.6f} {chain_unit}, need at least {gas_reserve:.6f} for gas.",
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        context.user_data["chain"] = chain
        context.user_data["max_withdrawable"] = balance - gas_reserve

    await query.edit_message_text(
        f"Enter the amount of {chain_unit} to withdraw (max {balance - gas_reserve:.6f} {chain_unit}, reserving {gas_reserve:.6f} {chain_unit} for gas):",
        parse_mode="Markdown"
    )
    return WITHDRAW_AMOUNT

async def withdraw_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chain = context.user_data["chain"]
    chain_unit = "SOL" if chain == "solana" else "TON"
    try:
        amount = float(update.message.text.strip())
        max_withdrawable = context.user_data["max_withdrawable"]
        if amount <= 0 or amount > max_withdrawable:
            await update.message.reply_text(
                f"Invalid amount. Enter a value between 0 and {max_withdrawable:.6f} {chain_unit}.",
                parse_mode="Markdown"
            )
            return WITHDRAW_AMOUNT
        context.user_data["withdraw_amount"] = amount
    except ValueError:
        await update.message.reply_text(f"Invalid amount. Enter a number (e.g., 1.5 {chain_unit}).", parse_mode="Markdown")
        return WITHDRAW_AMOUNT

    await update.message.reply_text(f"Please send the {chain_unit} destination address:", parse_mode="Markdown")
    return DESTINATION_ADDRESS

async def destination_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    destination_address = update.message.text.strip()
    context.user_data["destination_address"] = destination_address
    amount = context.user_data["withdraw_amount"]
    chain = context.user_data["chain"]
    chain_unit = "SOL" if chain == "solana" else "TON"

    keyboard = [
        [InlineKeyboardButton(f"Confirm Withdraw {amount:.6f} {chain_unit}", callback_data="confirm_withdraw")],
        [InlineKeyboardButton("Cancel", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Withdraw {amount:.6f} {chain_unit} to:\n`{destination_address}`\n\nConfirm the transaction:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return CONFIRM_WITHDRAW

async def confirm_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    amount = context.user_data["withdraw_amount"]
    destination_address = context.user_data["destination_address"]
    chain = context.user_data["chain"]
    chain_unit = "SOL" if chain == "solana" else "TON"

    async with await get_async_session() as session:
        wallet = await get_wallet(user_id, chain, session)
        encrypted_key = wallet.encrypted_private_key.encode('utf-8')
        private_key = CIPHER.decrypt(encrypted_key)  # Decrypted bytes

    try:
        if chain == "ton":
            mnemonic = private_key.decode('utf-8')  # TON uses mnemonic
            nano_amount = int(amount * 1_000_000_000)  # Convert to nanoTON
            tx_id = await send_ton_transaction(mnemonic, destination_address, nano_amount)
            explorer_url = f"https://tonscan.org/tx/{tx_id}"
        elif chain == "solana":
            # Placeholder for Solana (implement in blockchain/solana/withdraw.py)
            # keypair = Keypair.from_seed(private_key[:32])
            # tx_id = await send_solana_transaction(keypair, destination_address, int(amount * 1_000_000_000))
            # explorer_url = f"https://solscan.io/tx/{tx_id}"
            raise NotImplementedError("Solana withdrawal not yet implemented")
        else:
            raise ValueError(f"Unsupported chain: {chain}")

        msg = (
            f"Withdrawal Successful!\n"
            f"Sent {amount:.6f} {chain_unit} to `{destination_address}`\n"
            f"Tx: [{chain.capitalize()}Scan]({explorer_url})"
        )
        await query.edit_message_text(msg, parse_mode="Markdown")
        logger.info(f"User {user_id} withdrew {amount:.6f} {chain_unit} to {destination_address}")
    except Exception as e:
        await query.edit_message_text(f"Withdrawal failed: {str(e)}", parse_mode="Markdown")
        logger.error(f"{chain.capitalize()} withdrawal failed for user {user_id}: {str(e)}", exc_info=True)

    return ConversationHandler.END

async def cancel_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Withdrawal cancelled. Choose an option:", reply_markup=MAIN_MENU, parse_mode="Markdown")
    logger.info(f"User {update.effective_user.id} cancelled {context.user_data.get('chain', 'unknown')} withdrawal")
    return ConversationHandler.END

withdraw_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(withdraw_all, pattern="^withdraw_all_(solana|ton)$"),
        CallbackQueryHandler(withdraw_x, pattern="^withdraw_x_(solana|ton)$"),
    ],
    states={
        WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount_handler)],
        DESTINATION_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, destination_address_handler)],
        CONFIRM_WITHDRAW: [
            CallbackQueryHandler(confirm_withdraw, pattern="^confirm_withdraw$"),
            CallbackQueryHandler(cancel_withdraw, pattern="^main_menu$"),
        ]
    },
    fallbacks=[CallbackQueryHandler(cancel_withdraw, pattern="^main_menu$")]
)