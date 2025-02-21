import logging
import aiohttp
from solana.rpc.api import Client
from typing import Optional

logger = logging.getLogger(__name__)

# Multiple RPC endpoints for failover
RPC_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com",  # Public RPC
    "https://solana-mainnet.core.chainstack.com/YOUR_API_KEY",  # Chainstack (example)
    "https://ssc-dao.genesysgo.net"  # GenesysGo (example)
]
JUPITER_API = "https://quote-api.jup.ag/v6"

async def get_jupiter_client() -> Client:
    """Initialize Solana client with failover."""
    for rpc in RPC_ENDPOINTS:
        try:
            client = Client(rpc)
            await client.is_connected()  # Test connection
            logger.info(f"Using Solana RPC: {rpc}")
            return client
        except Exception as e:
            logger.warning(f"RPC {rpc} failed: {str(e)}")
    raise ConnectionError("All Solana RPC endpoints failed")

async def execute_solana_trade(wallet_pk: str, token_address: str, amount: float) -> Optional[str]:
    """
    Execute a trade on Jupiter for a Solana token.

    Args:
        wallet_pk: User’s wallet public key.
        token_address: Token to swap from.
        amount: Amount in SOL to spend.

    Returns:
        Transaction ID or None if failed.
    """
    try:
        client = await get_jupiter_client()
        async with aiohttp.ClientSession() as session:
            # Quote swap (SOL to token)
            quote_url = f"{JUPITER_API}/quote?inputMint=So11111111111111111111111111111111111111112&outputMint={token_address}&amount={int(amount * 1_000_000)}&slippageBps=50"
            async with session.get(quote_url) as resp:
                if resp.status != 200:
                    logger.error(f"Jupiter quote failed: {await resp.text()}")
                    return None
                quote = await resp.json()

            # Swap transaction (stubbed; requires wallet signing in production)
            swap_url = f"{JUPITER_API}/swap"
            payload = {
                "quoteResponse": quote,
                "userPublicKey": wallet_pk,
                "wrapAndUnwrapSol": True
            }
            async with session.post(swap_url, json=payload) as resp:
                if resp.status != 200:
                    logger.error(f"Jupiter swap failed: {await resp.text()}")
                    return None
                swap_data = await resp.json()
                tx_id = swap_data.get("swapTransaction")  # Simplified; actual TxID extraction varies
                logger.info(f"Executed Solana trade: {tx_id}")
                return tx_id

    except Exception as e:
        logger.error(f"Failed to execute Solana trade: {str(e)}")
        return None