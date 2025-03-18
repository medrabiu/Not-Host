import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes
from database.db import get_async_session
from services.wallet_management import get_wallet
from services.token_info import get_token_info, detect_chain
from services.utils import get_wallet_balance_and_usd, get_token_balance  # Import get_token_balance

logger = logging.getLogger(__name__)

async def positions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the user’s actual trading positions."""
    user_id = str(update.effective_user.id)
    query = update.callback_query
    await query.answer()

    # Initialize positions if not present (temporary storage in context.user_data)
    if "positions" not in context.user_data:
        context.user_data["positions"] = {}

    async with await get_async_session() as session:
        # Get user wallets
        sol_wallet = await get_wallet(user_id, "solana", session)
        ton_wallet = await get_wallet(user_id, "ton", session)

        if not sol_wallet and not ton_wallet:
            message = "📊 *Your Positions*\n\nYou don’t have any wallets set up yet. Start trading to see positions!"
            keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            logger.info(f"No wallets found for user {user_id} in positions")
            return

        # Fetch wallet balances (native tokens)
        sol_balance, sol_usd = await get_wallet_balance_and_usd(sol_wallet.public_key, "solana") if sol_wallet else (0.0, 0.0)
        ton_balance, ton_usd = await get_wallet_balance_and_usd(ton_wallet.public_key, "ton") if ton_wallet else (0.0, 0.0)

        # Fetch token positions from context.user_data
        positions = context.user_data["positions"]
        message = "📊 *Your Positions*\n\n"
        has_positions = False

        # Add native token positions if they exist
        if sol_balance > 0:
            sol_price = sol_usd / sol_balance if sol_balance > 0 else 0.0
            sol_entry = positions.get("SOL", {}).get("entry_price", sol_price)  # Default to current if no entry
            sol_pnl = (sol_price - sol_entry) * sol_balance
            message += (
                f"- *SOL*: {sol_balance:.4f} SOL\n"
                f"  Entry: ${sol_entry:.2f}, Current: ${sol_price:.2f}, PnL: {'+' if sol_pnl >= 0 else ''}${sol_pnl:.2f}\n"
            )
            has_positions = True

        if ton_balance > 0:
            ton_price = ton_usd / ton_balance if ton_balance > 0 else 0.0
            ton_entry = positions.get("TON", {}).get("entry_price", ton_price)  # Default to current if no entry
            ton_pnl = (ton_price - ton_entry) * ton_balance
            message += (
                f"- *TON*: {ton_balance:.4f} TON\n"
                f"  Entry: ${ton_entry:.2f}, Current: ${ton_price:.2f}, PnL: {'+' if ton_pnl >= 0 else ''}${ton_pnl:.2f}\n"
            )
            has_positions = True

        # Fetch and display other token positions
        if sol_wallet:
            for token_address, data in positions.items():
                chain = detect_chain(token_address)
                if chain == "solana":
                    token_balance = await get_token_balance(sol_wallet.public_key, token_address, "solana")
                    if token_balance > 0:
                        result = await get_token_info(token_address)
                        if result:
                            token_info, _ = result
                            current_price = float(token_info["price_usd"])
                            entry_price = data.get("entry_price", current_price)  # Default to current if no entry
                            pnl = (current_price - entry_price) * token_balance
                            message += (
                                f"- *{token_info['symbol']}*: {token_balance:.6f} {token_info['symbol']}\n"
                                f"  Entry: ${entry_price:.2f}, Current: ${current_price:.2f}, PnL: {'+' if pnl >= 0 else ''}${pnl:.2f}\n"
                            )
                            has_positions = True

        if ton_wallet:
            for token_address, data in positions.items():
                chain = detect_chain(token_address)
                if chain == "ton":
                    token_balance = await get_token_balance(ton_wallet.public_key, token_address, "ton")
                    if token_balance > 0:
                        result = await get_token_info(token_address)
                        if result:
                            token_info, _ = result
                            current_price = float(token_info["price_usd"])
                            entry_price = data.get("entry_price", current_price)  # Default to current if no entry
                            pnl = (current_price - entry_price) * token_balance
                            message += (
                                f"- *{token_info['symbol']}*: {token_balance:.6f} {token_info['symbol']}\n"
                                f"  Entry: ${entry_price:.2f}, Current: ${current_price:.2f}, PnL: {'+' if pnl >= 0 else ''}${pnl:.2f}\n"
                            )
                            has_positions = True

        if not has_positions:
            message += "You don’t hold any tokens yet. Start trading to build your positions!"

        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        logger.info(f"Displayed actual positions to user {user_id}")

# Export handler
positions_handler = CallbackQueryHandler(positions_handler, pattern="^positions$")