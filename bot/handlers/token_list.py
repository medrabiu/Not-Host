import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

async def fetch_token_prices():
    """Fetch real-time token prices from CoinGecko API."""
    url = "https://api.coingecko.com/api/v3/simple/price"
    tokens = {
        "ton-crystal": "TON",
        "tether": "USDT",
        "solana": "SOL",
        "usd-coin": "USDC",
        "shiba-inu": "SHIB"
    }
    
    params = {
        "ids": ",".join(tokens.keys()),
        "vs_currencies": "usd",
        "include_24hr_change": "true"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {tokens[key]: {
                        "price": data[key]["usd"],
                        "change": data[key]["usd_24h_change"]
                    } for key in data}
                else:
                    logger.error(f"API request failed with status {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching token prices: {str(e)}")
            return None

async def token_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display a list of tokens with real-time prices in AI Mode."""
    user_id = str(update.effective_user.id)
    query = update.callback_query
    await query.answer()

    # Fetch real-time prices
    token_data = await fetch_token_prices()
    
    if token_data:
        # Format the message with real-time data
        token_list = []
        for token, info in token_data.items():
            price = f"${info['price']:.6f}" if info['price'] < 1 else f"${info['price']:.2f}"
            change = f"+{info['change']:.1f}%" if info['change'] >= 0 else f"{info['change']:.1f}%"
            token_list.append(f"- *{token}*: {price} ({change})")
        
        message = (
            "📋 *Token List*\n\n"
            "Real-time token prices:\n" +
            "\n".join(token_list) +
            "\n\nData sourced from CoinGecko API. Prices update live!"
        )
    else:
        # Fallback message if API fails
        message = (
            "📋 *Token List (AI Mode)*\n\n"
            "Unable to fetch live prices right now. Here's a preview:\n"
            "- *TON*: $2.60 (+3.2%)\n"
            "- *USDT*: $1.00 (Stable)\n"
            "- *SOL*: $144.50 (+1.8%)\n"
            "- *USDC*: $1.00 (Stable)\n"
            "- *SHIB*: $0.000013 (+5.1%)\n\n"
            "Live data will be restored soon!"
        )

    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    logger.info(f"Displayed token list with live prices to user {user_id}")

# Export handler
token_list_handler = CallbackQueryHandler(token_list_handler, pattern="^token_list$")