import logging
import aiohttp
from urllib.parse import quote
import os

logger = logging.getLogger(__name__)

# ======== Configuration ========
IS_TESTNET = False
# API Keys and URLs
TON_KEY = os.getenv("TON_KEY") #  from toncenter via tg


TON_API_URL = "https://testnet.toncenter.com/api/v2" if IS_TESTNET else "https://toncenter.com/api/v2"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"


# ======== Functions ========

async def get_ton_balance(wallet_address: str) -> float:
    """
    Fetch the TON balance for a given wallet address from TON Center API.
    Supports both testnet and mainnet based on the IS_TESTNET flag.

    Args:
        wallet_address (str): The TON wallet address to query.

    Returns:
        float: Balance in TON (0.0 if failed).
    """
    try:
        encoded_address = quote(wallet_address, safe="")
        url = f"{TON_API_URL}/getAddressInformation?address={encoded_address}"
        headers = {"X-API-Key": TON_KEY} if TON_KEY != "YOUR_TONCENTER_API_KEY_HERE" else {}

        async with aiohttp.ClientSession() as session:
            logger.info(f"Querying TON balance ({'Testnet' if IS_TESTNET else 'Mainnet'}): {wallet_address}")
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        nanotons = int(data["result"]["balance"])
                        tons = nanotons / 1_000_000_000  # Convert nanotons to TON
                        logger.info(f"Fetched TON balance for {wallet_address}: {tons} TON")
                        return tons
                    else:
                        logger.error(f"TON API error for {wallet_address}: {data}")
                        return 0.0
                else:
                    logger.error(f"TON API request failed for {wallet_address}: {response.status}")
                    text = await response.text()
                    logger.error(f"Response details: {text}")
                    return 0.0
    except Exception as e:
        logger.error(f"Error fetching TON balance for {wallet_address}: {str(e)}")
        return 0.0


async def get_ton_price() -> float:
    """
    Fetch the current USD price of TON using the CoinGecko API.
    Always fetches mainnet price, as testnet doesn't have a market price.

    Returns:
        float: Current TON price in USD (0.0 if failed).
    """
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{COINGECKO_API_URL}/simple/price?ids=the-open-network&vs_currencies=usd"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    price = data.get("the-open-network", {}).get("usd", 0.0)
                    logger.info(f"Fetched TON price: ${price}")
                    return price
                else:
                    logger.error(f"Failed to fetch TON price: {response.status}")
                    return 0.0
    except Exception as e:
        logger.error(f"Error fetching TON price: {str(e)}")
        return 0.0

