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
    "gas_fee": "medium",
    "notifications": True,
    "wallet_format": "user_friendly",
    "currency": "USD"
}


async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompt user to choose which chain's settings to edit."""
    user_id = str(update.effective_user.id)

    # Initialize user settings if they don't exist
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
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(
            "⚙️ Which wallet’s settings would you like to edit?",
            reply_markup=reply_markup
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            "⚙️ Which wallet’s settings would you like to edit?",
            reply_markup=reply_markup
        )

    logger.info(f"Prompted user {user_id} to choose settings chain")


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle settings menu interactions."""
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    settings = context.user_data["settings"]

    # Extract data and current chain
    data = query.data
    chain = context.user_data.get("current_chain")

    if data.startswith("chain_settings_"):
        chain = data.split("_")[2]
        context.user_data["current_chain"] = chain
        await show_chain_settings_menu(query, context, chain)
        logger.info(f"User {user_id} selected {chain} settings")

    elif data == "set_gas_fee":
        await show_gas_fee_menu(query, chain)

    elif data.startswith("gas_"):
        gas_fee = data.split("_")[1]
        settings[chain]["gas_fee"] = gas_fee
        await show_chain_settings_menu(query, context, chain)
        logger.info(f"User {user_id} set {chain} gas fee to {gas_fee}")

    elif data == "toggle_notifications":
        settings[chain]["notifications"] = not settings[chain]["notifications"]
        await show_chain_settings_menu(query, context, chain)
        logger.info(f"User {user_id} toggled {chain} notifications to {settings[chain]['notifications']}")

    elif data == "set_wallet_format":
        await show_wallet_format_menu(query, chain)

    elif data.startswith("wallet_"):
        format_type = "_".join(data.split("_")[1:])
        settings[chain]["wallet_format"] = format_type
        await show_chain_settings_menu(query, context, chain)
        logger.info(f"User {user_id} set {chain} wallet format to {format_type}")

    elif data == "set_currency":
        await show_currency_menu(query, chain)

    elif data.startswith("currency_"):
        currency = data.split("_")[1]
        settings[chain]["currency"] = currency
        await show_chain_settings_menu(query, context, chain)
        logger.info(f"User {user_id} set {chain} currency to {currency}")

    elif data == "settings_done":
        await query.edit_message_text(
            f"✅ {chain.capitalize()} settings saved! Use /settings to adjust anytime."
        )
        logger.info(f"User {user_id} saved {chain} settings: {settings[chain]}")
        del context.user_data["current_chain"]

    elif data == "settings_back":
        await settings_handler(update, context)

    else:
        await query.edit_message_text("Unknown option. Please try again.")
        logger.warning(f"User {user_id} selected unknown option: {data}")


async def show_chain_settings_menu(query, context: ContextTypes.DEFAULT_TYPE, chain: str) -> None:
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

    await query.edit_message_text(
        f"⚙️ Adjust your {chain.upper()} trading settings below:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_gas_fee_menu(query, chain: str) -> None:
    """Show gas fee options."""
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


async def show_wallet_format_menu(query, chain: str) -> None:
    """Show wallet format options."""
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


async def show_currency_menu(query, chain: str) -> None:
    """Show currency options."""
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


# Export handlers
settings_command_handler = CommandHandler("settings", settings_handler)
settings_callback_handler = CallbackQueryHandler(
    settings_callback,
    pattern=r"^(set_|chain_|gas_|toggle_notifications|wallet_|currency_|settings_|main_menu)"
)
settings_input_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: None)

