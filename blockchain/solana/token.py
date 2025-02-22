import logging
import aiohttp
from solana.publickey import PublicKey
from typing import Dict, Optional
import ssl

logger = logging.getLogger(__name__)

DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens"
BIRDEYE_API = "https://public-api.birdeye.so/public/price"
JUPITER_API = "https://quote-api.jup.ag/v6"
SOL_MINT = "So11111111111111111111111111111111111111112"
BIRDEYE_API_KEY = "56e1ffe020b341ed98a4902f8dfd58e9"

async def get_solana_token_info(token_address: str) -> Optional[Dict]:
    """
    Fetch token info (name, price, liquidity, market cap) for a Solana token.
    Prioritizes Dexscreener, falls back to Birdeye, then Jupiter.

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

        # Disable SSL verification temporarily for testing
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            # Try Dexscreener
            dexscreener_url = f"{DEXSCREENER_API}/{token_address}"
            try:
                async with session.get(dexscreener_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        pair = data["pairs"][0] if data.get("pairs") else None
                        if pair:
                            token_info = {
                                "name": pair["baseToken"]["name"],
                                "symbol": pair["baseToken"]["symbol"],
                                "price_usd": float(pair["priceUsd"]),
                                "liquidity": float(pair["liquidity"]["usd"]),
                                "market_cap": float(pair.get("marketCap", pair.get("fdv", 0)))
                            }
                            logger.info(f"Fetched Solana token info from Dexscreener for {token_address}")
                            return token_info
                        else:
                            logger.warning(f"No Dexscreener pairs found for {token_address}")
                    else:
                        logger.warning(f"Dexscreener returned {resp.status} for {token_address}")
            except Exception as e:
                logger.error(f"Dexscreener failed for {token_address}: {str(e)}")

            # Fallback to Birdeye
            logger.info(f"Attempting Birdeye fallback for {token_address}")
            birdeye_url = f"{BIRDEYE_API}?address={token_address}"
            headers = {"X-API-KEY": BIRDEYE_API_KEY}
            try:
                async with session.get(birdeye_url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("success") and "data" in data:
                            price_usd = float(data["data"]["value"])
                        else:
                            raise ValueError("No price data from Birdeye")
                    else:
                        raise ValueError(f"Birdeye returned {resp.status}")
            except Exception as e:
                logger.error(f"Birdeye failed for {token_address}: {str(e)}")
            else:
                token_list_url = "https://token.jup.ag/strict"
                try:
                    async with session.get(token_list_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            tokens = await resp.json()
                            for token in tokens:
                                if token["address"] == token_address:
                                    name, symbol = token["name"], token["symbol"]
                                    break
                            else:
                                name, symbol = "Unknown", "UNK"
                        else:
                            logger.warning(f"Jupiter token list returned {resp.status}")
                            name, symbol = "Unknown", "UNK"
                except Exception as e:
                    logger.error(f"Jupiter token list fetch failed: {str(e)}")
                    name, symbol = "Unknown", "UNK"

                token_info = {
                    "name": name,
                    "symbol": symbol,
                    "price_usd": price_usd,
                    "liquidity": 0,
                    "market_cap": 0
                }
                logger.info(f"Fetched Solana token info from Birdeye for {token_address}")
                return token_info

            # Final fallback to Jupiter
            logger.info(f"Attempting Jupiter fallback for {token_address}")
            quote_url = f"{JUPITER_API}/quote?inputMint={SOL_MINT}&outputMint={token_address}&amount=1000000&slippageBps=50"
            async with session.get(quote_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    logger.error(f"Jupiter quote failed for {token_address}: {await resp.text()}")
                    return None
                quote = await resp.json()
                price_usd = float(quote["outAmount"]) / 1_000_000 * 150

            token_list_url = "https://token.jup.ag/strict"
            async with session.get(token_list_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
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

            token_info = {
                "name": name,
                "symbol": symbol,
                "price_usd": price_usd,
                "liquidity": 0,
                "market_cap": 0
            }
            logger.info(f"Fetched Solana token info from Jupiter fallback for {token_address}")
            return token_info

    except Exception as e:
        logger.error(f"Failed to fetch Solana token info for {token_address}: {str(e)}")
        return None