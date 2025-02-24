import logging
from typing import Dict, Optional, Tuple

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
    skip_links: bool = False
) -> str:
    """
    Format token info into a clear, readable Telegram message with dynamic trade details.

    Args:
        token_info: Dictionary containing token data.
        chain: The blockchain chain ('ton' or 'solana').
        wallet_balance: User's wallet balance for trade info.
        chain_price_usd: Current price of the chain's native token (TON or SOL) in USD.
        skip_links: Whether to skip social/website links (default: False).

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
    
    explorer_link = (
        f"https://tonscan.org/address/{token_info['address']}" if chain == "ton"
        else f"https://solscan.io/token/{token_info['address']}"
    )
    explorer_display = f"[{chain.capitalize()}scan]({explorer_link})"

    links_display = "Links: Nil"
    if not skip_links:
        social_links = token_info.get("social", [])
        website_links = token_info.get("websites", [])
        links = []
        if social_links or website_links:
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
    buy_amount = 1.5 if chain == "ton" else 0.01
    slippage = 22
    trade_amount_usd = buy_amount * chain_price_usd
    trade_output = (
        f"{buy_amount} {unit} (${trade_amount_usd:.2f}) → "
        f"{(trade_amount_usd / token_info['price_usd']):.2f} {token_info['symbol']} (${trade_amount_usd:.2f})"
        if token_info['price_usd'] > 0 else f"{buy_amount} {unit} (${trade_amount_usd:.2f}) → N/A"
    )

    return (
        f"**🟩 {token_info['symbol']} - {token_info['name']}** • {explorer_display}\n"
        f"Address: `{token_info['address']}`\n"
        f"────────────────────\n"
        f"💰 Market Cap: {market_cap_display}\n"
        f"🌊 Liquidity : {liquidity_display}\n"
        f"📊 Price     : {price_display}\n"
        f"────────────────────\n"
        f"🔐 Renounced: {renounced_display}  Mint: {mint_display}\n"
        f"👥 Holders  : {holders_display}\n"
        f"🔗 {links_display}\n"
        f"────────────────────\n"
        f"❗️ **Trade Details**\n"
        f"Buy Amount: {buy_amount} {unit} • Slippage: {slippage}%\n"
        f"Trade     : {trade_output}\n"
        f"💸 Balance : {wallet_balance} {unit}\n"
        f"☀️ *Set trade, verify, and tap BUY*"
    )