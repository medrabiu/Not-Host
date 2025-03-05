import logging
import aiohttp
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient

logger = logging.getLogger(__name__)

# Constants
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"  # Replace with your own RPC if needed
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

async def get_sol_balance(wallet_address: str) -> float:
    """
    Fetch the SOL balance for a given Solana wallet address.

    This function connects to a Solana RPC endpoint, retrieves the balance in lamports
    for the specified wallet address, and converts it to SOL.

    Args:
        wallet_address (str): The Solana wallet address to query (public key).

    Returns:
        float: The balance in SOL. Returns 0.0 if an error occurs.

    Raises:
        Exception: If the wallet address is invalid or the RPC request fails.
    """
    try:
        async with AsyncClient(SOLANA_RPC_URL) as client:
            pubkey = Pubkey.from_string(wallet_address)
            response = await client.get_balance(pubkey)
            lamports = response.value  # Balance in lamports
            sol = lamports / 1_000_000_000  # Convert lamports to SOL
            logger.info(f"Fetched SOL balance for {wallet_address}: {sol} SOL")
            return sol
    except Exception as e:
        logger.error(f"Error fetching SOL balance for {wallet_address}: {str(e)}")
        return 0.0

async def get_sol_price() -> float:
    """
    Fetch the current USD price of SOL using the CoinGecko API.

    This function makes an HTTP request to CoinGecko's simple price endpoint
    to retrieve the latest SOL price in USD.

    Returns:
        float: The current SOL price in USD. Returns 0.0 if an error occurs or
               if the API request fails.

    Raises:
        Exception: If the network request fails or the API response is malformed.
    """
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{COINGECKO_API_URL}/simple/price?ids=solana&vs_currencies=usd"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    price = data.get("solana", {}).get("usd", 0.0)
                    logger.info(f"Fetched SOL price: ${price}")
                    return price
                else:
                    logger.error(f"Failed to fetch SOL price: {response.status}")
                    return 0.0
    except Exception as e:
        logger.error(f"Error fetching SOL price: {str(e)}")
        return 0.0