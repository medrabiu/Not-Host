import logging
from typing import Dict, Optional
from blockchain.solana.token import get_solana_token_info
from blockchain.ton.token import get_ton_token_info

logger = logging.getLogger(__name__)

def detect_chain(token_address: str) -> str:
    """
    Detect blockchain from token address.

    Args:
        token_address: Token address to check.

    Returns:
        'solana' or 'ton' or raises ValueError if unknown.
    """
    if (40 <= len(token_address) <= 44):  # Solana Base58 length
        return "solana"
    elif (len(token_address) == 48 and token_address.startswith(("EQ", "UQ"))):  # TON format
        return "ton"
    else:
        logger.error(f"Unknown chain for address: {token_address}")
        raise ValueError("Invalid or unsupported token address")

async def get_token_info(token_address: str) -> Optional[Dict]:
    """
    Fetch token info based on detected chain.

    Args:
        token_address: Token address to query.

    Returns:
        Dict with token stats or None if failed.
    """
    try:
        chain = detect_chain(token_address)
        if chain == "solana":
          return await get_solana_token_info(token_address)  
        elif chain == "ton":
            return get_ton_token_info(token_address)
    except ValueError as e:
        logger.error(f"Token info failed: {str(e)}")
        return None

async def format_token_info(token_info: Dict) -> str:
    """
    Format token info into a Telegram-friendly string.

    Args:
        token_info: Dict with token stats.

    Returns:
        Formatted string for display.
    """
    return (
        f"Buy\n"
        f"{token_info['name']} (${token_info['symbol']})\n"
        f"├ {token_info['address']}\n"
        f"Balance: 0.001 SOL — Sol-snipe\n"
        f"└ #{token_info['symbol']} | 🌱 {token_info['age_days']}d |\n"
        f"📊 Token Stats\n"
        f" ├ USD:  ${token_info['price_usd']:.8f} ({token_info['price_change_24h']:+.1f}%)\n"
        f" ├ MC:   ${token_info['market_cap']/1000:.1f}K\n"
        f" ├ Vol:  ${token_info['volume_24h']/1000:.1f}K\n"
        f" ├ LP:   ${token_info['liquidity']/1000:.1f}K\n"
        f" ├ 1H:   {token_info['price_change_1h']:+.1f}% 🅑 {token_info['buys_1h']} Ⓢ {token_info['sells_1h']}\n"
        f" └ ATH:  ${token_info['ath']/1000:.1f}K ({token_info['ath_change']:+.1f}% / 5h)"
    )