# bot/handlers/wallet.py
import logging
import base58
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes
from database.db import get_async_session
from services.wallet_management import get_wallet
from services.utils import get_wallet_balance_and_usd, refresh_handler, main_menu_handler, add_common_buttons
from services.crypto import CIPHER
from solders.keypair import Keypair


logger = logging.getLogger(__name__)

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
         InlineKeyboardButton(f"Withdraw All {chain.upper()}", callback_data=f"withdraw_all_{chain}")],
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

wallet_handler = CallbackQueryHandler(wallet_handler, pattern="^wallet$")
wallet_callbacks = [
    CallbackQueryHandler(detailed_wallet_handler, pattern="^(solana_wallet|ton_wallet)$"),
    CallbackQueryHandler(lambda update, context: refresh_handler(update, context, update.callback_query.data, detailed_wallet_handler), 
                         pattern="^refresh_(solana|ton)_wallet$"),
    CallbackQueryHandler(reset_wallet, pattern="^reset_(solana|ton)_wallet$"),
    CallbackQueryHandler(export_wallet, pattern="^export_(solana|ton)_wallet$"),
    CallbackQueryHandler(import_wallet, pattern="^import_(solana|ton)_wallet$"),
    CallbackQueryHandler(main_menu_handler, pattern="^main_menu$")
]