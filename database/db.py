import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.models import engine, AsyncSessionFactory, Base, User  # Add Base import

logger = logging.getLogger(__name__)

async def init_db():
    """Initialize the database by creating all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

async def get_async_session() -> AsyncSession:
    """
    Create and return an asynchronous database session.

    Returns:
        An AsyncSession object. Caller must manage its lifecycle (commit/close).
    """
    try:
        session = AsyncSessionFactory()
        return session
    except Exception as e:
        logger.error(f"Failed to create async session: {str(e)}")
        raise

async def get_user(telegram_id: str, session: AsyncSession) -> Optional[User]:
    """
    Fetch a user by Telegram ID asynchronously.

    Args:
        telegram_id: User's Telegram ID.
        session: Active AsyncSession.

    Returns:
        User object or None if not found.
    """
    try:
        result = await session.execute(select(User).filter_by(telegram_id=telegram_id))
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Error fetching user {telegram_id}: {str(e)}")
        raise

async def add_user(telegram_id: str, session: AsyncSession) -> User:
    """
    Add a new user to the database asynchronously.

    Args:
        telegram_id: User's Telegram ID.
        session: Active AsyncSession.

    Returns:
        Newly created User object.

    Raises:
        Exception: If commit fails (e.g., duplicate telegram_id).
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