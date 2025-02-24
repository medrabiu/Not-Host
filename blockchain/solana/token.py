import logging
import aiohttp
from solana.publickey import PublicKey
from solana.rpc.async_api import AsyncClient
from typing import Dict, Optional
import os

logger = logging.getLogger(__name__)

DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens"
JUPYTER_PRICE_API = "https://api.jup.ag/price/v2"
JUPYTER_TOKEN_API = "https://api.jup.ag/tokens/v1/token"
JUPITER_SWAP_QUOTE_API = "https://api.jup.ag/swap/v1/quote"
SOL_MINT = "So11111111111111111111111111111111111111112"
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"  # Use your RPC if rate-limited

JUPITER_API_KEY = os.getenv("JUPITER_API_KEY", None)

async def get_sol_price(session: aiohttp.ClientSession) -> float:
    url = f"{JUPYTER_PRICE_API}?ids={SOL_MINT}&showExtraInfo=true"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("data") and SOL_MINT in data["data"]:
                    sol_price = float(data["data"][SOL_MINT]["price"])
                    logger.info(f"Fetched SOL price: ${sol_price}")
                    return sol_price
                logger.warning("No SOL price data from Jupiter")
            logger.warning(f"Jupiter Price API for SOL returned {resp.status}")
    except Exception as e:
        logger.error(f"Failed to fetch SOL price: {str(e)}")
    return 150.0

async def get_solana_token_info(token_address: str) -> Optional[Dict]:
    """
    Fetch Solana token info using Dexscreener first, then Jupiter, optimized for speed and completeness.

    Args:
        token_address: Solana token mint address.

    Returns:
        Dict with token stats or None if failed.
    """
    try:
        if not (40 <= len(token_address) <= 44):
            logger.error(f"Invalid Solana address length: {token_address}")
            return None
        try:
            PublicKey(token_address)
        except ValueError:
            logger.error(f"Invalid Solana address format: {token_address}")
            return None

        async with aiohttp.ClientSession() as session:
            sol_price_usd = await get_sol_price(session)

            # Try Dexscreener first (fast and rich data)
            token_info = await fetch_from_dexscreener(session, token_address, sol_price_usd)
            if token_info:
                logger.info(f"Fetched Solana token info from Dexscreener for {token_address}")
                return token_info

            # Fallback to Jupiter (authenticated or free)
            if JUPITER_API_KEY:
                token_info = await fetch_from_jupiter_authenticated(session, token_address, sol_price_usd)
                if token_info:
                    logger.info(f"Fetched detailed Solana token info from Jupiter (authenticated) for {token_address}")
                    return token_info
            else:
                token_info = await fetch_from_jupiter_free(session, token_address, sol_price_usd)
                if token_info:
                    logger.info(f"Fetched Solana token info from Jupiter (free tier) for {token_address}")
                    return token_info

            logger.error(f"No token info found for {token_address}")
            return None

    except Exception as e:
        logger.error(f"Failed to fetch Solana token info for {token_address}: {str(e)}")
        return None

async def fetch_from_dexscreener(session: aiohttp.ClientSession, token_address: str, sol_price_usd: float) -> Optional[Dict]:
    url = f"{DEXSCREENER_API}/{token_address}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status == 200:
                data = await resp.json()
                pair = data["pairs"][0] if data.get("pairs") else None
                if pair and pair.get("chainId") == "solana":
                    liquidity = pair.get("liquidity", {}).get("usd", 0.0)
                    price_usd = float(pair["priceUsd"])
                    trade_amount_usd = 0.01 * sol_price_usd
                    price_impact = (trade_amount_usd / (liquidity + trade_amount_usd)) * 100 if liquidity > 0 else 100.0
                    token_info = {
                        "name": pair["baseToken"]["name"],
                        "symbol": pair["baseToken"]["symbol"],
                        "address": token_address,
                        "price_usd": price_usd,
                        "liquidity": liquidity,
                        "market_cap": float(pair.get("marketCap", pair.get("fdv", 0))),
                        "price_impact": min(price_impact, 100.0),
                        "image": pair.get("info", {}).get("imageUrl", ""),
                        "holders_count": 0,  # Dexscreener doesn’t provide
                        "mintable": False,  # Not available
                        "renounced": False,  # Not available
                        "social": [item["url"] for item in pair.get("info", {}).get("socials", [])],
                        "websites": [site["url"] for site in pair.get("info", {}).get("websites", [])]
                    }
                    return token_info
            logger.warning(f"Dexscreener returned {resp.status} or no Solana pair for {token_address}")
            return None
    except Exception as e:
        logger.error(f"Dexscreener failed for {token_address}: {str(e)}")
        return None

async def fetch_from_jupiter_authenticated(session: aiohttp.ClientSession, token_address: str, sol_price_usd: float) -> Optional[Dict]:
    url = f"{JUPITER_SWAP_QUOTE_API}?inputMint={SOL_MINT}&outputMint={token_address}&amount=1000000&slippageBps=50"
    headers = {"Authorization": f"Bearer {JUPITER_API_KEY}"}
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status == 200:
                data = await resp.json()
                price_usd = float(data["outAmount"]) / 1_000_000 * sol_price_usd
                price_impact = float(data.get("priceImpactPct", 0.0)) * 100
                
                token_url = f"{JUPYTER_TOKEN_API}/{token_address}"
                async with session.get(token_url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as token_resp:
                    if token_resp.status == 200:
                        token_data = await token_resp.json()
                        name = token_data.get("name", "Unknown")
                        symbol = token_data.get("symbol", "UNK")
                    else:
                        name, symbol = "Unknown", "UNK"
                        logger.warning(f"Jupiter Token API returned {token_resp.status}")

                return {
                    "name": name,
                    "symbol": symbol,
                    "address": token_address,
                    "price_usd": price_usd,
                    "liquidity": 0.0,
                    "market_cap": 0.0,
                    "price_impact": price_impact,
                    "image": "",
                    "holders_count": 0,
                    "mintable": False,
                    "renounced": False,
                    "social": [],
                    "websites": []
                }
            logger.error(f"Jupiter Swap API returned {resp.status}")
            return None
    except Exception as e:
        logger.error(f"Jupiter authenticated fetch failed: {str(e)}")
        return None

async def fetch_from_jupiter_free(session: aiohttp.ClientSession, token_address: str, sol_price_usd: float) -> Optional[Dict]:
    price_url = f"{JUPYTER_PRICE_API}?ids={token_address}&showExtraInfo=true"
    token_url = f"{JUPYTER_TOKEN_API}/{token_address}"
    
    price_usd = 0.0
    name, symbol = "Unknown", "UNK"
    liquidity_usd = 0.0
    market_cap = 0.0
    price_impact = 0.0
    
    # Fetch price and market data
    try:
        async with session.get(price_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("data") and token_address in data["data"]:
                    token_data = data["data"][token_address]
                    price_usd = float(token_data["price"])
                    market_cap = float(token_data.get("extraInfo", {}).get("marketCap", 0.0)) or 0.0
                    liquidity_usd = float(token_data.get("extraInfo", {}).get("liquidity", 0.0)) or 0.0
                    price_impact = float(token_data.get("extraInfo", {}).get("depth", {}).get("buyPriceImpactRatio", {}).get("depth", {}).get("10", 0.0))
                else:
                    logger.warning(f"No price data from Jupiter free tier for {token_address}")
            else:
                logger.warning(f"Jupiter Price API returned {resp.status}")
    except Exception as e:
        logger.error(f"Jupiter Price API (free) failed: {str(e)}")

    # Fetch token metadata
    try:
        async with session.get(token_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status == 200:
                data = await resp.json()
                name = data.get("name", "Unknown")
                symbol = data.get("symbol", "UNK")
            else:
                logger.warning(f"Jupiter Token API returned {resp.status}")
    except Exception as e:
        logger.error(f"Jupiter Token API (free) failed: {str(e)}")

    # RPC fallback for holders_count, mintable, renounced (if critical)
    if price_usd > 0 or name != "Unknown":
        async with AsyncClient(SOLANA_RPC_URL) as rpc:
            try:
                mint_info = await rpc.get_token_supply(PublicKey(token_address))
                if mint_info.value:
                    holders_count = (await rpc.get_token_account_balance(PublicKey(token_address))).value.ui_amount or 0
                else:
                    holders_count = 0
                mint_data = await rpc.get_account_info(PublicKey(token_address))
                mintable = mint_data.value.data.parsed["info"]["mintAuthority"] is not None
                renounced = mint_data.value.data.parsed["info"]["mintAuthority"] is None
            except Exception as e:
                logger.error(f"RPC fetch failed for {token_address}: {str(e)}")
                holders_count, mintable, renounced = 0, False, False

        if price_impact == 0.0:
            trade_amount_usd = 0.01 * sol_price_usd
            assumed_liquidity = liquidity_usd if liquidity_usd > 0 else 100.0
            price_impact = (trade_amount_usd / (assumed_liquidity + trade_amount_usd)) * 100

        return {
            "name": name,
            "symbol": symbol,
            "address": token_address,
            "price_usd": price_usd,
            "liquidity": liquidity_usd,
            "market_cap": market_cap,
            "price_impact": min(price_impact, 100.0),
            "image": "",
            "holders_count": holders_count,
            "mintable": mintable,
            "renounced": renounced,
            "social": [],
            "websites": []
        }
    return None