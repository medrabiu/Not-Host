import logging
import aiohttp
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient

logger = logging.getLogger(__name__)

# Constants
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"  # Replace with your own RPC if needed
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

async def get_sol_balance(wallet_address: str) -> float:
    """Fetch SOL balance for a given Solana wallet address."""
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
    """Fetch the current USD price of SOL using CoinGecko API."""
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