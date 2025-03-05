import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.db import get_async_session, get_user
from database.models import User, Wallet
from blockchain.solana.wallet import create_solana_wallet
from blockchain.ton.wallet import create_ton_wallet

logger = logging.getLogger(__name__)

async def create_user_wallet(user_id: str, chain: str, session: AsyncSession) -> Optional[Wallet]:
    """
    Create a custodial wallet for a user on the specified chain asynchronously.

    This function generates a new wallet for the specified blockchain (Solana or TON),
    associates it with the user in the database, and encrypts the private key/mnemonic.
    It skips creation if a wallet already exists for the chain.

    Args:
        user_id (str): The user's Telegram ID.
        chain (str): The blockchain to create the wallet for ('solana' or 'ton').
        session (AsyncSession): An active SQLAlchemy asynchronous session.

    Returns:
        Optional[Wallet]: The created Wallet object if successful, None if a wallet
            already exists for the chain.

    Raises:
        ValueError: If the chain is unsupported or the user is not registered.
        Exception: If wallet creation or database operations fail (rolled back and logged).

    Notes:
        - Updates the user's has_wallet flag to True if this is their first wallet.
        - Performs a rollback on failure to maintain database consistency.
    """
    if chain not in ["solana", "ton"]:
        logger.error(f"Invalid chain specified: {chain}")
        raise ValueError(f"Unsupported chain: {chain}")

    try:
        # Check if user exists
        user = await get_user(user_id, session)
        if not user:
            logger.error(f"User {user_id} not found")
            raise ValueError(f"User {user_id} not registered")

        # Check if wallet already exists for this chain
        result = await session.execute(
            select(Wallet).filter_by(user_id=user.id, chain=chain)
        )
        existing_wallet = result.scalars().first()
        if existing_wallet:
            logger.info(f"Wallet already exists for user {user_id} on {chain}")
            return None

        # Create wallet based on chain
        if chain == "solana":
            public_key, encrypted_private_key = create_solana_wallet()
        else:  # ton
            public_key, encrypted_private_key = create_ton_wallet()

        # Store wallet in database
        wallet = Wallet(
            user_id=user.id,
            chain=chain,
            public_key=public_key,
            encrypted_private_key=encrypted_private_key
        )
        session.add(wallet)

        # Update user’s has_wallet flag if this is their first wallet
        if not user.has_wallet:
            user.has_wallet = True

        await session.commit()
        logger.info(f"Created {chain} wallet for user {user_id}: {public_key}")
        return wallet

    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to create wallet for {user_id} on {chain}: {str(e)}")
        raise

async def get_wallet(user_id: str, chain: str, session: AsyncSession) -> Optional[Wallet]:
    """
    Retrieve a user’s wallet for a specific chain asynchronously.

    This function queries the database to fetch the Wallet object associated with
    the specified user and blockchain.

    Args:
        user_id (str): The user's Telegram ID.
        chain (str): The blockchain to retrieve the wallet for ('solana' or 'ton').
        session (AsyncSession): An active SQLAlchemy asynchronous session.

    Returns:
        Optional[Wallet]: The Wallet object if found, None if no wallet exists
            or the user is not registered.

    Raises:
        ValueError: If the chain is unsupported.
        Exception: If the database query fails (logged and raised).

    Notes:
        - Returns None if the user or wallet is not found, rather than raising an error,
          to simplify downstream handling.
    """
    if chain not in ["solana", "ton"]:
        logger.error(f"Invalid chain specified: {chain}")
        raise ValueError(f"Unsupported chain: {chain}")

    try:
        user = await get_user(user_id, session)  # Now correctly imported
        if not user:
            logger.error(f"User {user_id} not found")
            return None

        result = await session.execute(
            select(Wallet).filter_by(user_id=user.id, chain=chain)
        )
        wallet = result.scalars().first()
        return wallet

    except Exception as e:
        logger.error(f"Error fetching wallet for {user_id} on {chain}: {str(e)}")
        raise