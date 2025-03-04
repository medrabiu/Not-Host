import logging
from typing import Dict, Optional, Tuple
from contextlib import asynccontextmanager
from telegram.ext import CallbackQueryHandler, ContextTypes, ConversationHandler
from blockchain.solana.token import get_solana_token_info, get_sol_price
from blockchain.ton.token import get_ton_token_info, get_ton_price
import aiohttp

logger = logging.getLogger(__name__)

def detect_chain(token_address: str) -> str:
    """
    Detect the blockchain chain based on the token address format.

    Args:
        token_address: The token address to analyze.

    Returns:
        The chain identifier ('ton' or 'solana').

    Raises:
        ValueError: If the address format is unrecognized.
    """
    logger.info(f"Detecting chain for address: {token_address}")
    if len(token_address) == 48 and token_address.startswith(("EQ", "UQ")):
        logger.info(f"TON address detected: {token_address}")
        return "ton"
    elif 40 <= len(token_address) <= 44 and not token_address.startswith(("EQ", "UQ")):
        logger.info(f"Solana address detected: {token_address}")
        return "solana"
    else:
        logger.error(f"Unknown chain for address: {token_address}")
        raise ValueError("Invalid or unsupported token address")

async def get_token_info(token_address: str) -> Optional[Tuple[Dict, float]]:
    """
    Fetch token information and native chain price based on the detected chain.

    Args:
        token_address: The token address to fetch info for.

    Returns:
        A tuple of (token_info dictionary, chain_price_usd), or None if fetching fails.
    """
    try:
        chain = detect_chain(token_address)
        logger.info(f"Fetching token info for {token_address} on chain: {chain}")
        
        async with aiohttp.ClientSession() as session:
            if chain == "solana":
                token_info = await get_solana_token_info(token_address)
                chain_price_usd = await get_sol_price(session)
            elif chain == "ton":
                token_info = await get_ton_token_info(token_address)
                chain_price_usd = await get_ton_price(session)
            else:
                return None
            
            if token_info:
                return token_info, chain_price_usd
            return None
    except ValueError as e:
        logger.error(f"Token info failed: {str(e)}")
        return None

async def format_token_info(
    token_info: Dict,
    chain: str,
    wallet_balance: float,
    chain_price_usd: float,
    context: Optional[ContextTypes.DEFAULT_TYPE] = None,
    show_explorer_link: bool = False  # Changed default to True
) -> str:
    """
    Format token info into a clear, readable Telegram message with dynamic trade details.

    Args:
        token_info: Dictionary containing token data.
        chain: The blockchain chain ('ton' or 'solana').
        wallet_balance: User's wallet balance for trade info.
        chain_price_usd: Current price of the chain's native token (TON or SOL) in USD.
        context: Optional Telegram context to access user_data for trade settings.
        show_explorer_link: Whether to show the blockchain explorer link (default: True).

    Returns:
        A formatted string for Telegram display.
    """
    price_display = f"${token_info['price_usd']:.9f}" if token_info['price_usd'] > 0 else "Nil"
    liquidity_display = (
        f"${token_info['liquidity']/1000:.2f}k" if token_info['liquidity'] >= 1000
        else f"${token_info['liquidity']:.2f}" if token_info['liquidity'] > 0 else "Nil"
    )
    market_cap_display = (
        f"${token_info['market_cap']/1000000:.2f}m" if token_info['market_cap'] >= 1000000
        else f"${token_info['market_cap']/1000:.2f}k" if token_info['market_cap'] > 0 else "Nil"
    )
    holders_display = (
        f"{token_info['holders_count']/1000000:.2f}m" if token_info['holders_count'] >= 1000000
        else f"{token_info['holders_count']/1000:.2f}k" if token_info['holders_count'] >= 1000
        else str(token_info['holders_count']) if token_info['holders_count'] > 0 else "Nil"
    )
    
    # Generate the explorer link, included by default if show_explorer_link is True
    explorer_link = (
        f"https://tonscan.org/address/{token_info['address']}" if chain == "ton"
        else f"https://solscan.io/token/{token_info['address']}"
    )
    explorer_display = f"[{chain.capitalize()}scan]({explorer_link})" if show_explorer_link else ""

    links_display = "Links: Nil"
    social_links = token_info.get("social", [])
    website_links = token_info.get("websites", [])
    if social_links or website_links:
        links = []
        for link in social_links:
            if "t.me" in link:
                links.append(f"[Telegram]({link})")
            elif "x.com" in link or "twitter.com" in link:
                links.append(f"[X]({link})")
        if website_links:
            links.append(f"[Web]({website_links[0]})")
        links_display = "Links: " + " • ".join(links) if links else "Links: Nil"

    mint_display = "🟢" if token_info['mintable'] else "🔴"
    renounced_display = "🟢" if token_info['renounced'] else "🔴"

    unit = "TON" if chain == "ton" else "SOL"
    default_amount = 0.5 if chain == "solana" else 1.5
    buy_amount = context.user_data.get("buy_amount", default_amount) if context else default_amount
    slippage = context.user_data.get("slippage", 5) if context else 5

    input_usd = buy_amount * chain_price_usd
    if token_info['price_usd'] > 0:
        output_tokens = input_usd / token_info['price_usd']
        slippage_factor = 1 - (slippage / 100)
        min_output_tokens = output_tokens * slippage_factor
        trade_output = (
            f"{buy_amount} {unit} (${input_usd:.2f}) → "
            f"{min_output_tokens:.6f} {token_info['symbol']} (${min_output_tokens * token_info['price_usd']:.2f})"
        )
    else:
        trade_output = f"{buy_amount} {unit} (${input_usd:.2f}) → N/A"

    # Conditionally include the explorer link in the header
    header = (
        f"**🟩 {token_info['symbol']} - {token_info['name']}** {explorer_display}\n"
        if show_explorer_link else
        f"**🟩 {token_info['symbol']} - {token_info['name']}**\n"
    )

    return (
        f"{header}"
        f"Address: `{token_info['address']}`\n"
        f"─────────────────\n"
        f"💰 Market Cap: {market_cap_display}\n"
        f"🌊 Liquidity : {liquidity_display}\n"
        f"📊 Price     : {price_display}\n"
        f"─────────────────\n"
        f"🔗 {links_display}\n"
        f"─────────────────\n"
        f"❗️ **Trade Details**\n"
        f"Buy Amount: {buy_amount} {unit} • Slippage: {slippage}%\n"
        f"Trade     : {trade_output}\n"
        f"💸 Balance : {wallet_balance:.2f} {unit}\n"
        f"☀️ *Set trade and tap Execute*"
    )

