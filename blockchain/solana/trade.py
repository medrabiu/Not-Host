import logging
import aiohttp
import base58
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solana.rpc.async_api import AsyncClient
from services.crypto import CIPHER
from typing import Dict

logger = logging.getLogger(__name__)

JUPITER_QUOTE_API = "https://quote-api.jup.ag/v6/quote"
JUPITER_SWAP_API = "https://quote-api.jup.ag/v6/swap"
RPC_ENDPOINT = "https://api.mainnet-beta.solana.com"  # Switch to devnet for testing

async def execute_solana_swap(wallet, token_mint: str, amount_sol: float, slippage_bps: int) -> Dict:
    """
    Execute a token swap on Solana using Jupiter DEX.

    Args:
        wallet: Wallet object with encrypted_private_key and public_key.
        token_mint: The mint address of the token to buy.
        amount_sol: Amount of SOL to spend.
        slippage_bps: Slippage tolerance in basis points (e.g., 50 = 0.5%).

    Returns:
        Dict with output_amount (in lamports) and tx_id.
    """
    try:
        # Decrypt private key and create keypair
        decrypted_key = CIPHER.decrypt(wallet.encrypted_private_key.encode('utf-8'))
        keypair = Keypair.from_seed(decrypted_key[:32])
        sender_pubkey = Pubkey.from_string(wallet.public_key)

        async with aiohttp.ClientSession() as session:
            # Step 1: Get quote from Jupiter
            quote_params = {
                "inputMint": "So11111111111111111111111111111111111111112",  # SOL
                "outputMint": token_mint,
                "amount": int(amount_sol * 1_000_000_000),  # SOL to lamports
                "slippageBps": int(slippage_bps * 100)  # Convert % to bps
            }
            async with session.get(JUPITER_QUOTE_API, params=quote_params) as resp:
                if resp.status != 200:
                    raise Exception(f"Quote API failed: {await resp.text()}")
                quote = await resp.json()
                output_amount = int(quote["outAmount"])

            # Step 2: Get swap transaction
            swap_params = {
                "quoteResponse": quote,
                "userPublicKey": str(sender_pubkey),
                "wrapAndUnwrapSol": True,
                "destinationTokenAccount": str(sender_pubkey)  # Simplified
            }
            async with session.post(JUPITER_SWAP_API, json=swap_params) as resp:
                if resp.status != 200:
                    raise Exception(f"Swap API failed: {await resp.text()}")
                swap_data = await resp.json()
                serialized_tx = swap_data["swapTransaction"]

            # Step 3: Deserialize and sign transaction
            async with AsyncClient(RPC_ENDPOINT) as client:
                tx = VersionedTransaction.from_bytes(base58.b58decode(serialized_tx))
                tx.sign([keypair])  # Sign with keypair

                # Step 4: Send transaction
                tx_id = await client.send_transaction(tx)
                logger.info(f"Swap transaction sent: {tx_id.value}")

        return {"output_amount": output_amount, "tx_id": tx_id.value}

    except Exception as e:
        logger.error(f"Failed to execute Solana swap: {str(e)}", exc_info=True)
        raise