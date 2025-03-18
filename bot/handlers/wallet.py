# bot/handlers/wallet.py
import logging
import base58
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from database.db import get_async_session
from services.wallet_management import get_wallet
from services.utils import get_wallet_balance_and_usd, refresh_handler, main_menu_handler, add_common_buttons
from services.crypto import CIPHER
from solders.keypair import Keypair
from blockchain.ton.withdraw import send_ton_transaction  # For TON withdrawals

logger = logging.getLogger(__name__)

# Conversation states for withdrawal
WITHDRAW_AMOUNT, DESTINATION_ADDRESS, CONFIRM_WITHDRAW = range(3)

WALLET_MAIN_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("Solana Wallet", callback_data="solana_wallet"),
     InlineKeyboardButton("TON Wallet", callback_data="ton_wallet")],
    [InlineKeyboardButton("Back", callback_data="main_menu")]
])

def get_detailed_wallet_menu(chain: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Wallet Reset", callback_data=f"reset_{chain}_wallet"),
         InlineKeyboardButton("Export Wallet", callback_data=f"export_{chain}_wallet")],
        [InlineKeyboardButton("Import Wallet", callback_data=f"import_{chain}_wallet"),
         InlineKeyboardButton(f"Withdraw All {chain.upper()}", callback_data=f"withdraw_x_{chain}_all")],
        [InlineKeyboardButton(f"Withdraw X {chain.upper()}", callback_data=f"withdraw_x_{chain}")]
    ]
    return add_common_buttons(keyboard, f"{chain}_wallet")

async def wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    async with await get_async_session() as session:
        sol_wallet = await get_wallet(user_id, "solana", session)
        ton_wallet = await get_wallet(user_id, "ton", session)
        sol_address = sol_wallet.public_key if sol_wallet else "Not set"
        ton_address = ton_wallet.public_key if ton_wallet else "Not set"

    msg = (
        "Your Wallets:\n"
        f"🔹 Solana: `{sol_address}`\n"
        f"🔸 TON: `{ton_address}`\n"
        "Select an option below:"
    )
    await query.edit_message_text(msg, reply_markup=WALLET_MAIN_MENU, parse_mode="Markdown")
    logger.info(f"Displayed wallet overview for user {user_id}")

async def detailed_wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    chain = "solana" if "solana" in query.data else "ton"
    chain_display = "Solana" if chain == "solana" else "TON"
    chain_unit = "SOL" if chain == "solana" else "TON"

    async with await get_async_session() as session:
        wallet = await get_wallet(user_id, chain, session)
        address = wallet.public_key if wallet else "Not set"
        balance, usd_value = await get_wallet_balance_and_usd(address, chain) if wallet else (0.0, 0.0)

    msg = (
        f"{chain_display} Wallet:\n"
        f"Address: `{address}`\n"
        f"Balance: {balance:.6f} {chain_unit} (${usd_value:.2f})\n\n"
        "Import wallet if you already have one."
    )
    markup = get_detailed_wallet_menu(chain)
    context.user_data[f"last_refresh_{chain}_wallet_msg"] = msg
    context.user_data[f"last_refresh_{chain}_wallet_markup"] = markup
    if "refresh" not in query.data:
        await query.edit_message_text(msg, reply_markup=markup, parse_mode="Markdown")
    logger.info(f"Displayed {chain_display} wallet details for user {user_id}")

async def reset_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chain = "solana" if "solana" in query.data else "ton"
    await query.edit_message_text(f"Resetting {chain} wallet - feature coming soon!", parse_mode="Markdown")
    logger.info(f"User {update.effective_user.id} requested {chain} wallet reset - stubbed")

async def export_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    chain = "solana" if "solana" in query.data else "ton"
    chain_display = "Solana" if chain == "solana" else "TON"

    async with await get_async_session() as session:
        wallet = await get_wallet(user_id, chain, session)
        if not wallet or not wallet.encrypted_private_key:
            await query.edit_message_text(f"No {chain_display} wallet found or private key unavailable.", parse_mode="Markdown")
            logger.warning(f"No private key for {chain_display} wallet for user {user_id}")
            return

        try:
            encrypted_key = wallet.encrypted_private_key.encode('utf-8')
            decrypted_bytes = CIPHER.decrypt(encrypted_key)

            if chain == "solana":
                keypair = Keypair.from_seed(decrypted_bytes[:32])
                full_keypair_bytes = keypair.secret() + bytes(keypair.pubkey())
                exported_key = base58.b58encode(full_keypair_bytes).decode('ascii')
                key_label = "Private Key"
            else:  # TON
                exported_key = decrypted_bytes.decode('utf-8')
                key_label = "Mnemonic Phrase"

        except Exception as e:
            await query.edit_message_text(f"Failed to export {chain_display} {key_label.lower()}.", parse_mode="Markdown")
            logger.error(f"Export failed for {chain_display} wallet for user {user_id}: {str(e)}", exc_info=True)
            return

    msg = (
        f"{chain_display} Wallet {key_label}:\n"
        f"`{exported_key}`\n\n"
        "⚠️ **Store this securely!** Do not share it publicly. This message will auto-delete in 1 minute if job queue is enabled."
    )
    sent_message = await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=msg,
        parse_mode="Markdown"
    )
    logger.info(f"Exported {chain_display} {key_label.lower()} for user {user_id}")

    if context.job_queue:
        context.job_queue.run_once(
            lambda ctx: ctx.bot.delete_message(chat_id=sent_message.chat_id, message_id=sent_message.message_id),
            60,
            data=sent_message.message_id,
            name=f"delete_export_{user_id}_{chain}"
        )
        logger.info(f"Scheduled deletion of {chain_display} {key_label.lower()} message for user {user_id} in 60 seconds")
    else:
        logger.warning(f"Job queue unavailable; {chain_display} message for user {user_id} will not auto-delete")

async def import_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chain = "solana" if "solana" in query.data else "ton"
    await query.edit_message_text(f"Importing {chain} wallet - feature coming soon!", parse_mode="Markdown")
    logger.info(f"User {update.effective_user.id} requested {chain} wallet import - stubbed")

async def withdraw_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    chain = "solana" if "solana" in query.data else "ton"
    chain_unit = "SOL" if chain == "solana" else "TON"
    gas_reserve = 0.0001 if chain == "solana" else 0.003 # Consistent gas reserve for both "All" and "X"
    is_withdraw_all = "_all" in query.data
    logger.info(f"withdraw_tokens triggered for user {user_id} with data: {query.data}, chain: {chain}, all: {is_withdraw_all}")

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
        max_withdrawable = balance - gas_reserve
        context.user_data["chain"] = chain
        context.user_data["max_withdrawable"] = max_withdrawable

        if is_withdraw_all:
            context.user_data["withdraw_amount"] = max_withdrawable
            await query.edit_message_text(
                f"Please send the {chain_unit} destination address to withdraw all {max_withdrawable:.6f} {chain_unit}:",
                parse_mode="Markdown"
            )
            logger.info(f"User {user_id} prompted for {chain_unit} destination address (withdraw all)")
            return DESTINATION_ADDRESS

    await query.edit_message_text(
        f"Enter the amount of {chain_unit} to withdraw (max {max_withdrawable:.6f} {chain_unit}, reserving {gas_reserve:.6f} {chain_unit} for gas):",
        parse_mode="Markdown"
    )
    logger.info(f"User {user_id} prompted for {chain_unit} amount (withdraw x)")
    return WITHDRAW_AMOUNT

async def withdraw_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    chain = context.user_data["chain"]
    chain_unit = "SOL" if chain == "solana" else "TON"
    logger.info(f"withdraw_amount_handler triggered for user {user_id}, chain: {chain}, input: {update.message.text}")
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
    logger.info(f"User {user_id} prompted for {chain_unit} destination address")
    return DESTINATION_ADDRESS

async def destination_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    destination_address = update.message.text.strip()
    context.user_data["destination_address"] = destination_address
    amount = context.user_data["withdraw_amount"]
    chain = context.user_data["chain"]
    chain_unit = "SOL" if chain == "solana" else "TON"
    logger.info(f"destination_address_handler triggered for user {user_id}, address: {destination_address}")

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
    logger.info(f"User {user_id} prompted for confirmation of {amount:.6f} {chain_unit} withdrawal")
    return CONFIRM_WITHDRAW

async def confirm_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    amount = context.user_data["withdraw_amount"]
    destination_address = context.user_data["destination_address"]
    chain = context.user_data["chain"]
    chain_unit = "SOL" if chain == "solana" else "TON"
    logger.info(f"confirm_withdraw triggered for user {user_id}, amount: {amount}, address: {destination_address}")

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

wallet_handler = CallbackQueryHandler(wallet_handler, pattern="^wallet$")
wallet_callbacks = [
    CallbackQueryHandler(detailed_wallet_handler, pattern="^(solana_wallet|ton_wallet)$"),
    CallbackQueryHandler(lambda update, context: refresh_handler(update, context, update.callback_query.data, detailed_wallet_handler), 
                         pattern="^refresh_(solana|ton)_wallet$"),
    CallbackQueryHandler(reset_wallet, pattern="^reset_(solana|ton)_wallet$"),
    CallbackQueryHandler(export_wallet, pattern="^export_(solana|ton)_wallet$"),
    CallbackQueryHandler(import_wallet, pattern="^import_(solana|ton)_wallet$"),
    CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
    ConversationHandler(
        entry_points=[
            CallbackQueryHandler(withdraw_tokens, pattern="^withdraw_x_(solana|ton)(_all)?$"),
        ],
        states={
            WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount_handler)],
            DESTINATION_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, destination_address_handler)],
            CONFIRM_WITHDRAW: [
                CallbackQueryHandler(confirm_withdraw, pattern="^confirm_withdraw$"),
                CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
            ]
        },
        fallbacks=[CallbackQueryHandler(main_menu_handler, pattern="^main_menu$")]
    )
]