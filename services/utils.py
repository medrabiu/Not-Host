import logging
from blockchain.solana.utils import get_sol_balance, get_sol_price
from blockchain.ton.utils import get_ton_balance, get_ton_price

logger = logging.getLogger(__name__)

async def get_wallet_balance_and_usd(wallet_address: str, chain: str) -> tuple[float, float]:
    """Get the balance and USD equivalent for a wallet address on a specified chain."""
    try:
        if chain.lower() == "solana":
            balance = await get_sol_balance(wallet_address)
            price = await get_sol_price()
        elif chain.lower() == "ton":
            balance = await get_ton_balance(wallet_address)
            price = await get_ton_price()
        else:
            logger.error(f"Unsupported chain: {chain}")
            return 0.0, 0.0

        usd_value = balance * price
        logger.info(f"Calculated USD value for {wallet_address} on {chain}: ${usd_value}")
        return balance, usd_value
    except Exception as e:
        logger.error(f"Error in get_wallet_balance_and_usd for {wallet_address}: {str(e)}")
        return 0.0, 0.0