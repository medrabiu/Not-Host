import logging
import aiohttp
from urllib.parse import quote 
import os

logger = logging.getLogger(__name__)

# Constants
TON_API_URL = "https://toncenter.com/api/v2"  
TON_API_KEY = "YOUR_TONCENTER_API_KEY_HERE" # os.getenv()
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

async def get_ton_balance(wallet_address: str) -> float:
    """
    Fetch the TON balance for a given TON wallet address using the TON Center API.

    This function queries the TON Center API's getAddressInformation endpoint to retrieve
    the balance in nanotons for the specified wallet address and converts it to TON.
    The wallet address is URL-encoded to handle special characters.

    Args:
        wallet_address (str): The TON wallet address to query.

    Returns:
        float: The balance in TON. Returns 0.0 if an error occurs or the API request fails.

    Raises:
        Exception: If the network request fails or the API response cannot be processed.

    Notes:
        - Requires a valid TON_API_KEY for authenticated requests; falls back to no headers if unchanged.
        - Logs detailed error information including response status and text on failure.
    """
    try:
        # URL encode the wallet address to handle special characters like '+'
        encoded_address = quote(wallet_address, safe='')
        url = f"{TON_API_URL}/getAddressInformation?address={encoded_address}"
        headers = {"X-API-Key": TON_API_KEY} if TON_API_KEY != "YOUR_TONCENTER_API_KEY_HERE" else {}
        
        async with aiohttp.ClientSession() as session:
            logger.info(f"Querying TON address: {wallet_address} (encoded: {encoded_address})")
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

    This function queries CoinGecko's simple price endpoint to retrieve the latest
    price of TON (The Open Network) in USD.

    Returns:
        float: The current TON price in USD. Returns 0.0 if an error occurs or
               the API request fails.

    Raises:
        Exception: If the network request fails or the API response is malformed.

    Notes:
        - Uses the CoinGecko ID 'the-open-network' for TON.
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