import logging
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from sqlalchemy.dialects.sqlite import insert
from database.models import engine, AsyncSessionFactory, Base, User, Watchlist

from sqlalchemy import update

logger = logging.getLogger(__name__)

async def init_db() -> None:
    """Initialize the database by creating all tables.

    Raises:
        Exception: If table creation fails due to database connectivity or schema issues.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

async def get_async_session() -> AsyncSession:
    """Create and return an asynchronous database session.

    Returns:
        AsyncSession: A new asynchronous session object.

    Raises:
        Exception: If session creation fails due to database connectivity issues.
    """
    try:
        session = AsyncSessionFactory()
        return session
    except Exception as e:
        logger.error(f"Failed to create async session: {str(e)}")
        raise

async def get_user(telegram_id: str, session: AsyncSession) -> Optional[User]:
    """Fetch a user by their Telegram ID asynchronously.

    Args:
        telegram_id (str): The Telegram ID of the user to fetch.
        session (AsyncSession): An active asynchronous database session.

    Returns:
        Optional[User]: The User object if found, otherwise None.

    Raises:
        Exception: If the query fails due to database errors.
    """
    try:
        result = await session.execute(select(User).filter_by(telegram_id=telegram_id))
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Error fetching user {telegram_id}: {str(e)}")
        raise

async def add_user(telegram_id: str, session: AsyncSession) -> User:
    """Add a new user to the database asynchronously.

    Args:
        telegram_id (str): The Telegram ID of the user to add.
        session (AsyncSession): An active asynchronous database session.

    Returns:
        User: The newly created User object.

    Raises:
        Exception: If the commit fails (e.g., due to duplicate telegram_id).
    """
    try:
        user = User(telegram_id=telegram_id)
        session.add(user)
        await session.commit()
        logger.info(f"Added user {telegram_id}")
        return user
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to add user {telegram_id}: {str(e)}")
        raise

async def add_watchlist_token(user_id: str, token_data: Dict, session: AsyncSession) -> None:
    """Add a token to the user's watchlist in the database, handling duplicates.

    Args:
        user_id (str): The Telegram ID of the user.
        token_data (Dict): A dictionary containing token details (e.g., address, symbol, name, chain).
        session (AsyncSession): An active asynchronous database session.

    Raises:
        Exception: If the database operation fails.
    """
    try:
        # Check if token already exists for this user
        existing = await session.execute(
            select(Watchlist).filter_by(user_id=user_id).where(
                Watchlist.token_data["address"].as_string() == token_data["address"]
            )
        )
        if existing.scalars().first():
            # Update existing entry
            stmt = (
                update(Watchlist)
                .where(
                    Watchlist.user_id == user_id,
                    Watchlist.token_data["address"].as_string() == token_data["address"]
                )
                .values(token_data=token_data)
            )
        else:
            # Insert new entry
            stmt = insert(Watchlist).values(user_id=user_id, token_data=token_data)

        await session.execute(stmt)
        await session.commit()
        logger.info(f"Added/Updated token {token_data['address']} to watchlist for user {user_id}")
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to add watchlist token for user {user_id}: {str(e)}")
        raise

async def get_watchlist_tokens(user_id: str, session: AsyncSession) -> List[Dict]:
    """Retrieve all tokens in the user's watchlist from the database.

    Args:
        user_id (str): The Telegram ID of the user.
        session (AsyncSession): An active asynchronous database session.

    Returns:
        List[Dict]: A list of token data dictionaries.

    Raises:
        Exception: If the query fails due to database errors.
    """
    try:
        result = await session.execute(select(Watchlist).filter_by(user_id=user_id))
        rows = result.scalars().all()
        return [row.token_data for row in rows] if rows else []
    except Exception as e:
        logger.error(f"Failed to fetch watchlist tokens for user {user_id}: {str(e)}")
        raise

async def delete_watchlist_token(user_id: str, token_address: str, session: AsyncSession) -> None:
    """Delete a token from the user's watchlist in the database.

    Args:
        user_id (str): The Telegram ID of the user.
        token_address (str): The address of the token to delete.
        session (AsyncSession): An active asynchronous database session.

    Raises:
        Exception: If the deletion fails due to database errors.
    """
    try:
        stmt = delete(Watchlist).where(
            Watchlist.user_id == user_id,
            Watchlist.token_data["address"].as_string() == token_address
        )
        await session.execute(stmt)
        await session.commit()
        logger.info(f"Deleted token {token_address} from watchlist for user {user_id}")
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to delete watchlist token {token_address} for user {user_id}: {str(e)}")
        raise
