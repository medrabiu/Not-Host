import logging
import aiohttp
from solana.rpc.api import Client
from solana.publickey import PublicKey
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Solana RPC endpoints with failover
RPC_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com",
    "https://ssc-dao.genesysgo.net",
    # Add your own (e.g., QuickNode) in production
]
JUPITER_API = "https://quote-api.jup.ag/v6"
SOL_MINT = "So11111111111111111111111111111111111111112"  # Wrapped SOL mint

async def get_solana_client() -> Optional[Client]:
    """Initialize Solana client with failover."""
    for rpc in RPC_ENDPOINTS:
        try:
            client = Client(rpc)
            if await client.is_connected():
                logger.info(f"Using Solana RPC: {rpc}")
                return client
        except Exception as e:
            logger.warning(f"RPC {rpc} failed: {str(e)}")
    logger.error("All Solana RPC endpoints failed")
    return None

async def get_solana_token_info(token_address: str) -> Optional[Dict]:
    """
    Fetch real token info for a Solana token address using Jupiter and RPC.

    Args:
        token_address: Solana token mint address (e.g., FFXVWS3F...).

    Returns:
        Dict with token stats or None if failed.
    """
    try:
        # Validate address format (Base58, ~44 chars)
        if not (40 <= len(token_address) <= 44):
            logger.error(f"Invalid Solana address length: {token_address}")
            return None
        try:
            PublicKey(token_address)  # Ensure it’s a valid public key
        except ValueError:
            logger.error(f"Invalid Solana address: {token_address}")
            return None

        async with aiohttp.ClientSession() as session:
            # Fetch price quote from Jupiter (SOL -> Token)
            quote_url = f"{JUPITER_API}/quote?inputMint={SOL_MINT}&outputMint={token_address}&amount=1000000&slippageBps=50"
            async with session.get(quote_url) as resp:
                if resp.status != 200:
                    logger.error(f"Jupiter quote failed for {token_address}: {await resp.text()}")
                    return None
                quote = await resp.json()
                price_usd = float(quote["outAmount"]) / 1_000_000 * 150  # Assuming 1 SOL = $150; adjust with real SOL price

            # Fetch token metadata from RPC
            client = await get_solana_client()
            if not client:
                return None

            # Get token supply (simplified; assumes decimals = 6)
            supply_resp = await client.get_token_supply(PublicKey(token_address))
            if "value" not in supply_resp:
                logger.error(f"Failed to get supply for {token_address}")
                return None
            supply = supply_resp["value"]["uiAmount"]
            market_cap = supply * price_usd

            # Placeholder for other stats (requires external API or Raydium pools)
            token_info = {
                "name": "Unknown",  # Requires token list or Metaplex metadata
                "symbol": "UNK",    # Placeholder
                "address": token_address,
                "price_usd": price_usd,
                "price_change_24h": 0.0,  # Requires historical data
                "market_cap": market_cap,
                "volume_24h": 0,    # Stub; fetch from Jupiter/Raydium
                "liquidity": 0,     # Stub; fetch from pool data
                "price_change_1h": 0.0,  # Stub
                "buys_1h": 0,       # Stub
                "sells_1h": 0,      # Stub
                "ath": market_cap * 1.2,  # Arbitrary stub
                "ath_change": 0.0,  # Stub
                "age_days": (datetime.now() - datetime(2023, 1, 1)).days  # Arbitrary stub
            }

            # Optional: Fetch name/symbol from Jupiter token list
            token_list_url = "https://token.jup.ag/strict"
            async with session.get(token_list_url) as resp:
                if resp.status == 200:
                    tokens = await resp.json()
                    for token in tokens:
                        if token["address"] == token_address:
                            token_info["name"] = token["name"]
                            token_info["symbol"] = token["symbol"]
                            break

            logger.info(f"Fetched real Solana token info for {token_address}")
            return token_info

    except Exception as e:
        logger.error(f"Failed to fetch Solana token info for {token_address}: {str(e)}")
        return None