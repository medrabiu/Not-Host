import logging
import aiohttp
from solana.publickey import PublicKey
from typing import Dict, Optional

logger = logging.getLogger(__name__)

DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens"
JUPITER_API = "https://quote-api.jup.ag/v6"
SOL_MINT = "So11111111111111111111111111111111111111112"

async def get_solana_token_info(token_address: str) -> Optional[Dict]:
    """
    Fetch minimal token info (name, price, liquidity, market cap) for a Solana token.

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
            # Try Dexscreener
            dexscreener_url = f"{DEXSCREENER_API}/{token_address}"
            try:
                async with session.get(dexscreener_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        pair = data["pairs"][0] if data.get("pairs") else None
                        if pair:
                            token_info = {
                                "name": pair["baseToken"]["name"],
                                "symbol": pair["baseToken"]["symbol"],
                                "price_usd": float(pair["priceUsd"]),
                                "liquidity": float(pair["liquidity"]["usd"]),
                                "market_cap": float(pair.get("fdv", 0))
                            }
                            logger.info(f"Fetched Solana token info from Dexscreener for {token_address}")
                            return token_info
                        else:
                            logger.warning(f"No Dexscreener pairs for {token_address}")
                    else:
                        logger.warning(f"Dexscreener API returned {resp.status} for {token_address}")
            except Exception as e:
                logger.error(f"Dexscreener failed for {token_address}: {str(e)}")

            # Fallback to Jupiter
            quote_url = f"{JUPITER_API}/quote?inputMint={SOL_MINT}&outputMint={token_address}&amount=1000000&slippageBps=50"
            try:
                async with session.get(quote_url) as resp:
                    if resp.status != 200:
                        logger.error(f"Jupiter quote failed for {token_address}: {await resp.text()}")
                        return None
                    quote = await resp.json()
                    price_usd = float(quote["outAmount"]) / 1_000_000 * 150  # Stub SOL at $150
            except Exception as e:
                logger.error(f"Jupiter quote fetch failed for {token_address}: {str(e)}")
                return None

            token_list_url = "https://token.jup.ag/strict"
            try:
                async with session.get(token_list_url) as resp:
                    if resp.status != 200:
                        logger.error(f"Jupiter token list failed for {token_address}: {await resp.text()}")
                        return None
                    tokens = await resp.json()
                    for token in tokens:
                        if token["address"] == token_address:
                            name, symbol = token["name"], token["symbol"]
                            break
                    else:
                        name, symbol = "Unknown", "UNK"
            except Exception as e:
                logger.error(f"Jupiter token list fetch failed for {token_address}: {str(e)}")
                return None

            token_info = {
                "name": name,
                "symbol": symbol,
                "price_usd": price_usd,
                "liquidity": 0,  # Stub
                "market_cap": 0  # Stub
            }
            logger.info(f"Fetched Solana token info from Jupiter fallback for {token_address}")
            return token_info

    except Exception as e:
        logger.error(f"Failed to fetch Solana token info for {token_address}: {str(e)}")
        return None