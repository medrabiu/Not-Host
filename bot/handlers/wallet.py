import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.wallet_management import create_user_wallet, get_wallet

logger = logging.getLogger(__name__)

async def wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the 'wallet' button click, display user’s wallets or create them if missing.

    Edge Cases:
    - User has no wallets yet.
    - Database or wallet creation errors.
    """
    query = update.callback_query
    await query.answer()  # Acknowledge the callback

    try:
        user_id = str(update.effective_user.id)

        # Get or create Solana wallet
        solana_wallet = get_wallet(user_id, "solana")
        if not solana_wallet:
            solana_wallet = create_user_wallet(user_id, "solana")

        # Get or create TON wallet
        ton_wallet = get_wallet(user_id, "ton")
        if not ton_wallet:
            ton_wallet = create_user_wallet(user_id, "ton")

        # Build response
        if solana_wallet and ton_wallet:
            msg = (
                "Your Wallets:\n"
                f"🔹 Solana: `{solana_wallet.public_key}`\n"
                f"🔸 TON: `{ton_wallet.public_key}`\n"
                "Deposit funds to start trading!"
            )
        else:
            msg = "Failed to retrieve or create wallets. Try again later."
            logger.error(f"Wallet retrieval failed for {user_id}")

        await query.edit_message_text(msg, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in wallet handler for {user_id}: {str(e)}")
        await query.edit_message_text("An error occurred while fetching your wallets.")
