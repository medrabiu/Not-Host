import logging
import aiohttp
from solana.rpc.async_api import AsyncClient
from tonsdk.utils import Address
from tonsdk.provider import TonCenterClient
from tonsdk.utils import b64str_to_bytes

logger = logging.getLogger(__name__)

# Constants
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"  # Use your own RPC if needed
TON_API_URL = "https://toncenter.com/api/v2"  # TonCenter API endpoint
TON_API_KEY = "your_toncenter_api_key"  # Replace with your TonCenter API key
JUPITER_API_URL = "https://price.jup.ag/v4/price"  # Jupiter price API for SOL

async def get_sol_balance(wallet_address: str) -> float:
    """Fetch SOL balance for a given Solana wallet address."""
    try:
        async with AsyncClient(SOLANA_RPC_URL) as client:
            response = await client.get_balance(wallet_address)
            if "result" in response and "value" in response["result"]:
                lamports = response["result"]["value"]
                sol = lamports / 1_000_000_000  # Convert lamports to SOL
                logger.info(f"Fetched SOL balance for {wallet_address}: {sol} SOL")
                return sol
            else:
                logger.error(f"Failed to fetch SOL balance for {wallet_address}: {response}")
                return 0.0
    except Exception as e:
        logger.error(f"Error fetching SOL balance for {wallet_address}: {str(e)}")
        return 0.0

async def get_ton_balance(wallet_address: str) -> float:
    """Fetch TON balance for a given TON wallet address."""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{TON_API_URL}/getAddressBalance?address={wallet_address}"
            headers = {"X-API-Key": TON_API_KEY} if TON_API_KEY else {}
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        nanotons = int(data["result"])
                        tons = nanotons / 1_000_000_000  # Convert nanotons to TON
                        logger.info(f"Fetched TON balance for {wallet_address}: {tons} TON")
                        return tons
                    else:
                        logger.error(f"TON API error for {wallet_address}: {data}")
                        return 0.0
                else:
                    logger.error(f"TON API request failed for {wallet_address}: {response.status}")
                    return 0.0
    except Exception as e:
        logger.error(f"Error fetching TON balance for {wallet_address}: {str(e)}")
        return 0.0

async def get_crypto_price(symbol: str) -> float:
    """Fetch the current USD price for SOL or TON using Jupiter API."""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{JUPITER_API_URL}?ids={symbol}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    price = data["data"].get(symbol, {}).get("price", 0.0)
                    logger.info(f"Fetched price for {symbol}: ${price}")
                    return price
                else:
                    logger.error(f"Failed to fetch price for {symbol}: {response.status}")
                    return 0.0
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {str(e)}")
        return 0.0

async def get_wallet_balance_and_usd(wallet_address: str, chain: str) -> tuple[float, float]:
    """Get the balance and USD equivalent for a wallet address."""
    try:
        if chain.lower() == "solana":
            balance = await get_sol_balance(wallet_address)
            price = await get_crypto_price("SOL")
        elif chain.lower() == "ton":
            balance = await get_ton_balance(wallet_address)
            price = await get_crypto_price("TONCOIN")  # Jupiter uses "TONCOIN" for TON
        else:
            logger.error(f"Unsupported chain: {chain}")
            return 0.0, 0.0

        usd_value = balance * price
        return balance, usd_value
    except Exception as e:
        logger.error(f"Error in get_wallet_balance_and_usd for {wallet_address}: {str(e)}")
        return 0.0, 0.0