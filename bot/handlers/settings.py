import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

logger = logging.getLogger(__name__)

# Default chain-specific settings (removed slippage)
DEFAULT_TON_SETTINGS = {
    "gas_fee": "medium",  # low, medium, high
    "notifications": True,
    "wallet_format": "user_friendly",
    "currency": "USD"
}

DEFAULT_SOLANA_SETTINGS = {
    "gas_fee": "medium",  # low, medium, high
    "notifications": True,
    "wallet_format": "user_friendly",
    "currency": "USD"
}

async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompt user to choose which chain's settings to edit."""
    user_id = str(update.effective_user.id)
    
    if "settings" not in context.user_data:
        context.user_data["settings"] = {
            "ton": DEFAULT_TON_SETTINGS.copy(),
            "solana": DEFAULT_SOLANA_SETTINGS.copy()
        }
    
    keyboard = [
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        [InlineKeyboardButton("TON Settings", callback_data="chain_settings_ton"),
         InlineKeyboardButton("Solana Settings", callback_data="chain_settings_solana")]
    ]
    await update.message.reply_text(
        "⚙️ Which wallet’s settings would you like to edit?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    logger.info(f"Prompted user {user_id} to choose settings chain")

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle settings menu interactions."""
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    settings = context.user_data["settings"]

    if query.data.startswith("chain_settings_"):
        chain = query.data.split("_")[2]
        context.user_data["current_chain"] = chain
        await show_chain_settings_menu(query, context, chain)
        logger.info(f"User {user_id} selected {chain} settings")

    elif query.data == "set_gas_fee":
        chain = context.user_data["current_chain"]
        keyboard = [
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
            [InlineKeyboardButton("Low", callback_data="gas_low"),
             InlineKeyboardButton("Medium", callback_data="gas_medium"),
             InlineKeyboardButton("High", callback_data="gas_high")],
            [InlineKeyboardButton("Back", callback_data="settings_back")]
        ]
        await query.edit_message_text(
            f"Select gas fee preference for {chain.upper()}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("gas_"):
        chain = context.user_data["current_chain"]
        gas_fee = query.data.split("_")[1]
        settings[chain]["gas_fee"] = gas_fee
        await show_chain_settings_menu(query, context, chain)
        logger.info(f"User {user_id} set {chain} gas fee to {gas_fee}")

    elif query.data == "toggle_notifications":
        chain = context.user_data["current_chain"]
        settings[chain]["notifications"] = not settings[chain]["notifications"]
        await show_chain_settings_menu(query, context, chain)
        logger.info(f"User {user_id} toggled {chain} notifications to {settings[chain]['notifications']}")

    elif query.data == "set_wallet_format":
        chain = context.user_data["current_chain"]
        keyboard = [
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
            [InlineKeyboardButton("User Friendly", callback_data="wallet_user_friendly"),
             InlineKeyboardButton("Raw", callback_data="wallet_raw")],
            [InlineKeyboardButton("Back", callback_data="settings_back")]
        ]
        await query.edit_message_text(
            f"Select wallet address format for {chain.upper()}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("wallet_"):
        chain = context.user_data["current_chain"]
        format_type = "_".join(query.data.split("_")[1:])
        settings[chain]["wallet_format"] = format_type
        await show_chain_settings_menu(query, context, chain)
        logger.info(f"User {user_id} set {chain} wallet format to {format_type}")

    elif query.data == "set_currency":
        chain = context.user_data["current_chain"]
        keyboard = [
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
            [InlineKeyboardButton("USD", callback_data="currency_USD"),
             InlineKeyboardButton("EUR", callback_data="currency_EUR")],
            [InlineKeyboardButton("Back", callback_data="settings_back")]
        ]
        await query.edit_message_text(
            f"Select fiat currency for {chain.upper()}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data.startswith("currency_"):
        chain = context.user_data["current_chain"]
        currency = query.data.split("_")[1]
        settings[chain]["currency"] = currency
        await show_chain_settings_menu(query, context, chain)
        logger.info(f"User {user_id} set {chain} currency to {currency}")

    elif query.data == "settings_done":
        chain = context.user_data["current_chain"]
        await query.edit_message_text(
            f"✅ {chain.capitalize()} settings saved! Use /settings to adjust anytime."
        )
        logger.info(f"User {user_id} saved {chain} settings: {settings[chain]}")
        del context.user_data["current_chain"]

    elif query.data == "settings_back":
        keyboard = [
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
            [InlineKeyboardButton("TON Settings", callback_data="chain_settings_ton"),
             InlineKeyboardButton("Solana Settings", callback_data="chain_settings_solana")]
        ]
        await query.edit_message_text(
            "⚙️ Which wallet’s settings would you like to edit?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def show_chain_settings_menu(message_or_query, context: ContextTypes.DEFAULT_TYPE, chain: str) -> None:
    """Display chain-specific settings menu."""
    settings = context.user_data["settings"][chain]
    keyboard = [
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        [InlineKeyboardButton(f"Gas Fee: {settings['gas_fee'].capitalize()}", callback_data="set_gas_fee")],
        [InlineKeyboardButton(f"Notifications: {'On' if settings['notifications'] else 'Off'}", callback_data="toggle_notifications")],
        [InlineKeyboardButton(f"Wallet Format: {settings['wallet_format'].replace('_', ' ').capitalize()}", callback_data="set_wallet_format")],
        [InlineKeyboardButton(f"Currency: {settings['currency']}", callback_data="set_currency")],
        [InlineKeyboardButton("Done", callback_data="settings_done")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(message_or_query, "message"):  # CallbackQuery
        await message_or_query.edit_message_text(
            f"⚙️ Adjust your {chain.upper()} trading settings below:",
            reply_markup=reply_markup
        )
    else:  # Message
        await message_or_query.reply_text(
            f"⚙️ Adjust your {chain.upper()} trading settings below:",
            reply_markup=reply_markup
        )

# Export handlers
settings_command_handler = CommandHandler("settings", settings_handler)
settings_callback_handler = CallbackQueryHandler(settings_callback, pattern=r"^(set_|chain_|gas_|toggle_notifications|wallet_|currency_|settings_|main_menu)")
settings_input_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: None)  # No text input needed