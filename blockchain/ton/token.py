import logging
import aiohttp
from typing import Dict, Optional

logger = logging.getLogger(__name__)

TON_API_JETTON_URL = "https://tonapi.io/v2/jettons"
TON_API_RATES_URL = "https://tonapi.io/v2/rates"
TON_API_MARKETS_URL = "https://tonapi.io/v2/jettons/{address}/markets"
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens"

async def get_ton_price(session: aiohttp.ClientSession) -> float:
    url = f"{TON_API_RATES_URL}?currencies=usd&tokens=ton"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status == 200:
                data = await resp.json()
                ton_price = float(data["rates"]["TON"]["prices"]["USD"])
                logger.info(f"Fetched TON price: ${ton_price}")
                return ton_price
            logger.warning(f"TON Price API returned {resp.status}")
    except Exception as e:
        logger.error(f"Failed to fetch TON price: {str(e)}")
    return 5.0

async def get_ton_token_info(token_address: str) -> Optional[Dict]:
    """
    Fetch TON token info using Dexscreener as primary source, with TonAPI as fallback.

    Args:
        token_address: TON token address (Jetton master contract).

    Returns:
        Dict with token stats or None if failed.
    """
    try:
        if not (len(token_address) == 48 and token_address.startswith(("EQ", "UQ"))):
            logger.error(f"Invalid TON address format: {token_address}")
            return None

        async with aiohttp.ClientSession() as session:
            ton_price_usd = await get_ton_price(session)

            # Fetch Jetton metadata and total supply from TonAPI
            url = f"{TON_API_JETTON_URL}/{token_address}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    logger.warning(f"TON Jetton API returned {resp.status}")
                    return None
                data = await resp.json()
                logger.info(f"Raw TON Jetton API response for {token_address}: {data}")
                metadata = data.get("metadata", {})
                total_supply = int(data.get("total_supply", "0")) / 10**int(metadata.get("decimals", "9"))

            # Fetch token price from TonAPI rates
            rates_url = f"{TON_API_RATES_URL}?currencies=usd&tokens={token_address}"
            price_usd = 0.0
            try:
                async with session.get(rates_url, timeout=aiohttp.ClientTimeout(total=5)) as rates_resp:
                    if rates_resp.status == 200:
                        rates_data = await rates_resp.json()
                        price_usd = float(rates_data["rates"].get(token_address, {}).get("prices", {}).get("USD", 0.0))
                        logger.info(f"Fetched token price: ${price_usd} for {token_address}")
                    else:
                        logger.warning(f"TON Rates API returned {rates_resp.status}")
            except Exception as e:
                logger.error(f"Failed to fetch token price: {str(e)}")

            # Initial values
            market_cap = total_supply * price_usd if price_usd > 0 else 0.0
            liquidity_usd = 0.0
            social = metadata.get("social", [])
            websites = metadata.get("websites", [])

            # Try Dexscreener first for liquidity, market data, and links
            try:
                async with session.get(f"{DEXSCREENER_API}/{token_address}", timeout=aiohttp.ClientTimeout(total=5)) as dex_resp:
                    if dex_resp.status == 200:
                        dex_data = await dex_resp.json()
                        logger.info(f"Raw Dexscreener API response for {token_address}: {dex_data}")
                        pair = dex_data["pairs"][0] if dex_data.get("pairs") else None
                        if pair and pair.get("chainId") == "ton":
                            liquidity_usd = float(pair["liquidity"]["usd"])
                            market_cap = float(pair.get("marketCap", market_cap))
                            social = [item["url"] for item in pair.get("info", {}).get("socials", [])]
                            websites = [site["url"] for site in pair.get("info", {}).get("websites", [])]
                            logger.info(f"Fetched Dexscreener data: liquidity=${liquidity_usd}, market_cap=${market_cap}, social={social}, websites={websites}")
                    else:
                        logger.warning(f"Dexscreener API returned {dex_resp.status}")
            except Exception as e:
                logger.error(f"Failed to fetch from Dexscreener: {str(e)}")

            # Fallback to TonAPI markets if Dexscreener fails or lacks liquidity
            if liquidity_usd == 0.0:
                markets_url = TON_API_MARKETS_URL.format(address=token_address)
                try:
                    async with session.get(markets_url, timeout=aiohttp.ClientTimeout(total=5)) as markets_resp:
                        if markets_resp.status == 200:
                            markets_data = await markets_resp.json()
                            logger.info(f"Raw TON Markets API response for {token_address}: {markets_data}")
                            if markets_data.get("markets"):
                                market = markets_data["markets"][0]
                                market_cap = float(market.get("market_cap_usd", market_cap))
                                liquidity_usd = float(market.get("liquidity_usd", 0.0))
                                logger.info(f"Fetched market data: market_cap=${market_cap}, liquidity=${liquidity_usd}")
                        else:
                            logger.warning(f"TON Markets API returned {markets_resp.status}")
                except Exception as e:
                    logger.error(f"Failed to fetch market data from TonAPI: {str(e)}")

            trade_amount_usd = 0.02 * ton_price_usd
            price_impact = (trade_amount_usd / (liquidity_usd + trade_amount_usd)) * 100 if liquidity_usd > 0 else 100.0

            token_info = {
                "name": metadata.get("name", "Unknown"),
                "symbol": metadata.get("symbol", "UNK"),
                "address": token_address,
                "price_usd": price_usd,
                "liquidity": liquidity_usd,
                "market_cap": market_cap,
                "price_impact": min(price_impact, 100.0),
                "image": metadata.get("image", ""),
                "holders_count": data.get("holders_count", 0),
                "mintable": data.get("mintable", False),
                "renounced": False,
                "social": social,  # Use Dexscreener if available, else TonAPI
                "websites": websites  # Use Dexscreener if available, else TonAPI
            }
            logger.info(f"Fetched TON token info: {token_info}")
            return token_info

    except Exception as e:
        logger.error(f"Failed to fetch TON token info for {token_address}: {str(e)}")
        return None