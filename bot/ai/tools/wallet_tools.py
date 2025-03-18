import logging
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import get_async_session
from services.utils import get_wallet_balance_and_usd
from services.wallet_management import get_wallet
from services.crypto import CIPHER
from solders.keypair import Keypair
from blockchain.ton.withdraw import send_ton_transaction
import base58
from services.token_info import get_token_info, detect_chain
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

@tool
async def show_wallet_info(user_id: int, chain: str) -> str:
    """Show wallet details for the given chain (solana or ton).

    Args:
        user_id: The Telegram user ID.
        chain: The blockchain ('solana' or 'ton').
    """
    async with await get_async_session() as session:
        wallet = await get_wallet(str(user_id), chain, session)
        if not wallet:
            return f"No {chain.capitalize()} wallet found."
        address = wallet.public_key
        balance, usd_value = await get_wallet_balance_and_usd(address, chain)
        chain_unit = "SOL" if chain == "solana" else "TON"
        return (
            f"{chain.capitalize()} Wallet:\n"
            f"Address: `{address}`\n"
            f"Balance: {balance:.6f} {chain_unit} (${usd_value:.2f})"
        )

@tool
async def export_wallet_key(user_id: int, chain: str) -> str:
    """Export the private key or mnemonic for the given chain (solana or ton).

    Args:
        user_id: The Telegram user ID.
        chain: The blockchain ('solana' or 'ton').
    """
    async with await get_async_session() as session:
        wallet = await get_wallet(str(user_id), chain, session)
        if not wallet or not wallet.encrypted_private_key:
            return f"No {chain.capitalize()} wallet or private key found."
        try:
            encrypted_key = wallet.encrypted_private_key.encode('utf-8')
            decrypted_bytes = CIPHER.decrypt(encrypted_key)
            chain_display = "Solana" if chain == "solana" else "TON"
            if chain == "solana":
                keypair = Keypair.from_seed(decrypted_bytes[:32])
                exported_key = base58.b58encode(keypair.secret() + bytes(keypair.pubkey())).decode('ascii')
                key_label = "Private Key"
            else:
                exported_key = decrypted_bytes.decode('utf-8')
                key_label = "Mnemonic Phrase"
            return (
                f"{chain_display} Wallet {key_label}:\n"
                f"`{exported_key}`\n\n"
                "⚠️ **Store this securely!** Do not share it."
            )
        except Exception as e:
            logger.error(f"Export failed for {chain} wallet for user {user_id}: {str(e)}")
            return f"Failed to export {chain.capitalize()} key."

@tool
async def withdraw_tokens(user_id: int, chain: str, amount: float, destination_address: str) -> str:
    """Withdraw tokens from the given chain to a destination address.

    Args:
        user_id: The Telegram user ID.
        chain: The blockchain ('solana' or 'ton').
        amount: The amount to withdraw.
        destination_address: The destination wallet address.
    """
    chain_unit = "SOL" if chain == "solana" else "TON"
    gas_reserve = 0.0001 if chain == "solana" else 0.003
    async with await get_async_session() as session:
        wallet = await get_wallet(str(user_id), chain, session)
        if not wallet:
            return f"No {chain.capitalize()} wallet found."
        balance, _ = await get_wallet_balance_and_usd(wallet.public_key, chain)
        if balance <= gas_reserve:
            return f"Insufficient {chain_unit}. Balance: {balance:.6f}, need > {gas_reserve:.6f}."
        max_withdrawable = balance - gas_reserve
        if amount <= 0 or amount > max_withdrawable:
            return f"Invalid amount. Must be between 0 and {max_withdrawable:.6f} {chain_unit}."
        encrypted_key = wallet.encrypted_private_key.encode('utf-8')
        private_key = CIPHER.decrypt(encrypted_key)
        try:
            if chain == "ton":
                mnemonic = private_key.decode('utf-8')
                nano_amount = int(amount * 1_000_000_000)
                tx_id = await send_ton_transaction(mnemonic, destination_address, nano_amount)
                return (
                    f"Withdrew {amount:.6f} {chain_unit} to `{destination_address}`\n"
                    f"Tx: [TONScan](https://tonscan.org/tx/{tx_id})"
                )
            return "Solana withdrawal not yet implemented."
        except Exception as e:
            logger.error(f"Withdrawal failed for user {user_id}: {str(e)}")
            return f"Withdrawal failed: {str(e)}"


@tool
async def get_token_details(token_address: str) -> str:
    """Fetch liquidity and market cap for a token address."""
    try:
        chain = detect_chain(token_address)
        result = await get_token_info(token_address)
        if not result:
            return "No dice, fam! Couldn’t snag details for that token."
        
        token_info, _ = result
        liquidity = (
            f"${token_info['liquidity']/1000:.2f}k" if token_info['liquidity'] >= 1000
            else f"${token_info['liquidity']:.2f}" if token_info['liquidity'] > 0 else "Nil"
        )
        market_cap = (
            f"${token_info['market_cap']/1000000:.2f}m" if token_info['market_cap'] >= 1000000
            else f"${token_info['market_cap']/1000:.2f}k" if token_info['market_cap'] > 0 else "Nil"
        )
        name = token_info.get("name", "Unknown")
        symbol = token_info.get("symbol", "N/A")
        
        return (
            f"Token scoop for `{token_address}`:\n"
            f"📛 Name: {name} ({symbol})\n"
            f"🌊 Liquidity: {liquidity}\n"
            f"💰 Market Cap: {market_cap}"
        )
    except ValueError:
        return "That’s a dodgy address, mate! Needs to be a proper Solana or TON token."
    except Exception as e:
        logger.error(f"Error fetching token details for {token_address}: {str(e)}")
        return "Whoops, hit a snag grabbing that token’s deets!"
    
