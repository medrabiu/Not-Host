import logging
from typing import Dict, Optional
from blockchain.solana.token import get_solana_token_info
from blockchain.ton.token import get_ton_token_info

logger = logging.getLogger(__name__)

def detect_chain(token_address: str) -> str:
    if 40 <= len(token_address) <= 44:
        return "solana"
    elif len(token_address) == 48 and token_address.startswith(("EQ", "UQ")):
        return "ton"
    else:
        raise ValueError("Invalid or unsupported token address")

async def get_token_info(token_address: str) -> Optional[Dict]:
    try:
        chain = detect_chain(token_address)
        if chain == "solana":
            return await get_solana_token_info(token_address)
        elif chain == "ton":
            return await get_ton_token_info(token_address)
    except ValueError as e:
        logger.error(f"Token info failed: {str(e)}")
        return None

async def format_token_info(token_info: Dict, chain: str, wallet_balance: float) -> str:
    """Format minimal token info without buy options in text."""
    return (
        f"Buy ${token_info['symbol']} - {token_info['name']} 📈\n"
        f"Token CA: {token_info['address']}\n"
        f"Wallet Balance: {wallet_balance:.2f} {chain.upper()}\n"
        f"Price: ${token_info['price_usd']:.6f} - Liq: ${token_info['liquidity']/1000:.1f}K\n"
        f"Market Cap: ${token_info['market_cap']/1000:.1f}K"
    )